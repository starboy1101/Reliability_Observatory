import threading
from dataclasses import dataclass
from typing import Any, Protocol

from .config import Settings


@dataclass(frozen=True, slots=True)
class Generation:
    content: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str


class InferenceEngine(Protocol):
    @property
    def ready(self) -> bool: ...

    def load(self) -> None: ...

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        max_new_tokens: int,
    ) -> Generation: ...


class TransformersEngine:
    def __init__(self, settings: Settings, device: str | None = None) -> None:
        self.settings = settings
        self._tokenizer: Any = None
        self._model: Any = None
        self._torch: Any = None
        self._device = device or "auto"
        self._generation_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._tokenizer is not None and self._model is not None

    def load(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(self.settings.torch_threads)
        if self._device == "auto":
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        model_dtype = torch.bfloat16 if self._device == "cuda" else torch.float32
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.settings.model_id,
            revision=self.settings.model_revision,
            local_files_only=self.settings.local_files_only,
        )
        self._tokenizer.truncation_side = "left"
        self._model = AutoModelForCausalLM.from_pretrained(
            self.settings.model_id,
            revision=self.settings.model_revision,
            local_files_only=self.settings.local_files_only,
            dtype=model_dtype,
        )
        # ZeroGPU emulates CUDA during module initialization, so this placement is
        # intentionally performed before the decorated request function runs.
        self._model.to(self._device).eval()
        self._torch = torch

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        max_new_tokens: int,
    ) -> Generation:
        if not self.ready or self._torch is None:
            raise RuntimeError("Model is not loaded")

        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self._tokenizer(
            prompt,
            add_special_tokens=False,
            max_length=self.settings.max_input_tokens,
            truncation=True,
            return_tensors="pt",
        )
        inputs = {name: tensor.to(self._device) for name, tensor in inputs.items()}
        prompt_tokens = int(inputs["input_ids"].shape[-1])
        generation_options: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": temperature > 0,
            "pad_token_id": self._tokenizer.eos_token_id,
        }
        if temperature > 0:
            generation_options.update({"temperature": temperature, "top_p": top_p})

        with self._generation_lock, self._torch.inference_mode():
            output_ids = self._model.generate(**inputs, **generation_options)

        generated_ids = output_ids[0, prompt_tokens:]
        completion_tokens = int(generated_ids.shape[-1])
        content = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        if not content:
            content = "I could not produce a response for this input."
        finish_reason = "length" if completion_tokens >= max_new_tokens else "stop"
        return Generation(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=finish_reason,
        )

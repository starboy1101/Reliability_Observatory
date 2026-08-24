import os
from dataclasses import dataclass, field

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _boolean(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True, slots=True)
class Settings:
    model_id: str = MODEL_ID
    model_revision: str = MODEL_REVISION
    model_alias: str = "reliability-observatory-sut"
    max_input_tokens: int = 2048
    max_output_tokens: int = 128
    max_messages: int = 32
    max_request_characters: int = 16_000
    torch_threads: int = 2
    gpu_duration_seconds: int = 30
    local_files_only: bool = False
    api_key: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls) -> "Settings":
        model_id = os.getenv("MODEL_ID", MODEL_ID).strip()
        model_revision = os.getenv("MODEL_REVISION", MODEL_REVISION).strip()
        if not model_id or not model_revision:
            raise ValueError("MODEL_ID and MODEL_REVISION must not be empty")
        return cls(
            model_id=model_id,
            model_revision=model_revision,
            model_alias=os.getenv("MODEL_ALIAS", "reliability-observatory-sut").strip(),
            max_input_tokens=_integer("MAX_INPUT_TOKENS", 2048, 128, 8192),
            max_output_tokens=_integer("MAX_OUTPUT_TOKENS", 128, 1, 1024),
            max_messages=_integer("MAX_MESSAGES", 32, 1, 128),
            max_request_characters=_integer(
                "MAX_REQUEST_CHARACTERS", 16_000, 256, 100_000
            ),
            torch_threads=_integer("TORCH_THREADS", 2, 1, 16),
            gpu_duration_seconds=_integer("GPU_DURATION_SECONDS", 30, 5, 120),
            local_files_only=_boolean("MODEL_LOCAL_FILES_ONLY", False),
            api_key=os.getenv("SPACE_API_KEY") or None,
        )

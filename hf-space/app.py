# ruff: noqa: I001 -- ZeroGPU requires importing spaces before CUDA-aware packages.
import logging

import spaces  # Must be imported before CUDA-aware libraries on ZeroGPU.
import gradio as gr

from model_api.config import Settings
from model_api.inference import TransformersEngine
from model_api.service import ModelService

logging.basicConfig(level=logging.INFO)
settings = Settings.from_environment()
engine = TransformersEngine(settings, device="cuda")
engine.load()
service = ModelService(settings, engine)

app = gr.Server(title="Reliability Observatory ZeroGPU Target")


@app.api(name="chat", concurrency_limit=1)
@spaces.GPU(duration=settings.gpu_duration_seconds)
def chat(
    messages_json: str,
    temperature: float = 0.0,
    max_tokens: int = 128,
    request: gr.Request | None = None,
) -> dict:
    """Generate one bounded response for an adversarial evaluation case."""
    headers = dict(request.headers) if request is not None else {}
    return service.chat(
        messages_json,
        temperature,
        max_tokens,
        headers.get("x-space-api-key"),
    )


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "service": "Reliability Observatory ZeroGPU Target",
        "model": settings.model_id,
        "model_revision": settings.model_revision,
        "sdk": "gradio",
        "api_name": "chat",
    }


@app.get("/healthz")
async def health() -> dict[str, object]:
    return {
        "status": "ready" if engine.ready and settings.api_key else "not_configured",
        "model": settings.model_id,
    }


if __name__ == "__main__":
    app.launch()

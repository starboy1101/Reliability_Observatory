import json
import logging
import math
import secrets
from typing import Any

from pydantic import ValidationError

from .config import Settings
from .inference import InferenceEngine
from .schemas import MessageBatch

logger = logging.getLogger("model_api")


class ModelService:
    """Validate one Gradio request and return a stable, JSON-safe response."""

    def __init__(self, settings: Settings, engine: InferenceEngine) -> None:
        self.settings = settings
        self.engine = engine

    def chat(
        self,
        messages_json: str,
        temperature: float,
        max_tokens: int,
        supplied_api_key: str | None,
    ) -> dict[str, Any]:
        expected = self.settings.api_key
        if expected is None:
            raise RuntimeError("Inference authentication is not configured")
        if supplied_api_key is None or not secrets.compare_digest(
            supplied_api_key, expected
        ):
            raise PermissionError("Invalid Space API key")
        if not isinstance(messages_json, str) or len(messages_json) > (
            self.settings.max_request_characters + 4_096
        ):
            raise ValueError("Chat content is too large")

        try:
            decoded = json.loads(messages_json)
            batch = MessageBatch.model_validate({"messages": decoded})
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise ValueError("messages_json must contain a valid chat message array") from exc

        if len(batch.messages) > self.settings.max_messages:
            raise ValueError("Too many chat messages")
        if sum(len(message.content) for message in batch.messages) > (
            self.settings.max_request_characters
        ):
            raise ValueError("Chat content is too large")

        try:
            normalized_temperature = float(temperature)
            requested_tokens = int(max_tokens)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid generation parameters") from exc
        if not math.isfinite(normalized_temperature) or not 0 <= normalized_temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if requested_tokens < 1:
            raise ValueError("max_tokens must be positive")
        bounded_tokens = min(requested_tokens, self.settings.max_output_tokens)

        generation = self.engine.generate(
            [message.model_dump() for message in batch.messages],
            temperature=normalized_temperature,
            top_p=1.0,
            max_new_tokens=bounded_tokens,
        )
        logger.info(
            "generation_complete model=%s prompt_tokens=%d completion_tokens=%d",
            self.settings.model_id,
            generation.prompt_tokens,
            generation.completion_tokens,
        )
        return {
            "content": generation.content,
            "model": self.settings.model_id,
            "model_revision": self.settings.model_revision,
            "finish_reason": generation.finish_reason,
            "usage": {
                "prompt_tokens": generation.prompt_tokens,
                "completion_tokens": generation.completion_tokens,
                "total_tokens": generation.prompt_tokens + generation.completion_tokens,
            },
        }

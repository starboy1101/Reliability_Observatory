import json
import logging

import pytest
from conftest import FakeEngine

from model_api.config import MODEL_ID, MODEL_REVISION, Settings
from model_api.service import ModelService


def messages_json(content: str = "A synthetic evaluation prompt.") -> str:
    return json.dumps([{"role": "user", "content": content}])


def test_chat_returns_stable_metadata_and_clamps_output(
    service: ModelService,
    fake_engine: FakeEngine,
) -> None:
    result = service.chat(messages_json(), 0, 512, "test-space-key")

    assert result == {
        "content": "A bounded model response.",
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 11,
            "completion_tokens": 5,
            "total_tokens": 16,
        },
    }
    assert fake_engine.calls[0]["max_new_tokens"] == 128
    assert fake_engine.calls[0]["temperature"] == 0


def test_chat_requires_the_server_secret(service: ModelService) -> None:
    with pytest.raises(PermissionError, match="Invalid Space API key"):
        service.chat(messages_json(), 0, 64, None)
    with pytest.raises(PermissionError, match="Invalid Space API key"):
        service.chat(messages_json(), 0, 64, "wrong")


def test_missing_space_key_fails_closed(fake_engine: FakeEngine) -> None:
    service = ModelService(Settings(api_key=None), fake_engine)
    with pytest.raises(RuntimeError, match="authentication is not configured"):
        service.chat(messages_json(), 0, 64, None)


@pytest.mark.parametrize(
    ("payload", "temperature", "max_tokens", "message"),
    [
        ("not-json", 0, 64, "valid chat message array"),
        (json.dumps([{"role": "tool", "content": "x"}]), 0, 64, "valid chat"),
        (messages_json(), float("nan"), 64, "temperature"),
        (messages_json(), 0, 0, "max_tokens"),
    ],
)
def test_invalid_requests_are_rejected(
    service: ModelService,
    payload: str,
    temperature: float,
    max_tokens: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        service.chat(payload, temperature, max_tokens, "test-space-key")


def test_content_limit_is_enforced(fake_engine: FakeEngine) -> None:
    settings = Settings(max_request_characters=256, api_key="test-space-key")
    service = ModelService(settings, fake_engine)
    with pytest.raises(ValueError, match="too large"):
        service.chat(messages_json("x" * 257), 0, 64, "test-space-key")


def test_logs_do_not_include_prompt_content(
    service: ModelService,
    caplog,
) -> None:  # type: ignore[no-untyped-def]
    sensitive_canary = "PRIVATE-CANARY-NEVER-LOG"
    with caplog.at_level(logging.INFO, logger="model_api"):
        service.chat(messages_json(sensitive_canary), 0, 64, "test-space-key")
    assert sensitive_canary not in caplog.text

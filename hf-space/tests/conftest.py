import pytest

from model_api.config import MODEL_ID, MODEL_REVISION, Settings
from model_api.inference import Generation
from model_api.service import ModelService


class FakeEngine:
    def __init__(self) -> None:
        self.ready = True
        self.calls: list[dict[str, object]] = []

    def load(self) -> None:
        self.ready = True

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        max_new_tokens: int,
    ) -> Generation:
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_new_tokens": max_new_tokens,
            }
        )
        return Generation(
            content="A bounded model response.",
            prompt_tokens=11,
            completion_tokens=5,
            finish_reason="stop",
        )


@pytest.fixture
def fake_engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        max_output_tokens=128,
        api_key="test-space-key",
    )


@pytest.fixture
def service(settings: Settings, fake_engine: FakeEngine) -> ModelService:
    return ModelService(settings, fake_engine)

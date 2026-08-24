import os

import pytest

from model_api.config import Settings
from model_api.inference import TransformersEngine


@pytest.mark.model
@pytest.mark.skipif(
    os.getenv("RUN_MODEL_TEST") != "1",
    reason="Set RUN_MODEL_TEST=1 to download and run the pinned model.",
)
def test_real_model_generates_one_response() -> None:
    settings = Settings.from_environment()
    engine = TransformersEngine(settings)
    engine.load()
    result = engine.generate(
        [{"role": "user", "content": "Answer with only the word ready."}],
        temperature=0,
        top_p=1,
        max_new_tokens=16,
    )
    assert result.content
    assert result.prompt_tokens > 0
    assert result.completion_tokens > 0

import asyncio
import sys
import types

import httpx

from app.config import Settings
from app.enums import PromptCategory, TargetKind
from app.evaluators import DeepEvalEvaluator
from app.schemas import TargetConfig
from app.suite import generate_suite
from app.targets import GenerationResult, OpenAICompatibleTarget, TargetError


def test_openai_compatible_adapter_uses_server_managed_key() -> None:
    seen: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("authorization")
        seen["payload"] = __import__("json").loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "cannot verify"}}]})

    async def exercise() -> None:
        settings = Settings(
            allow_private_target_urls=True,
            target_host_allowlist="models.example.test",
            openai_compatible_api_key="server-secret",
        )
        config = TargetConfig(
            kind=TargetKind.OPENAI_COMPATIBLE,
            model="local-test-model",
            base_url="https://models.example.test/v1",
        )
        target = OpenAICompatibleTarget(config, settings)
        configured_headers = dict(target.client.headers)
        await target.client.aclose()
        target.client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), headers=configured_headers
        )
        try:
            result = await target.generate(generate_suite()[0])
        finally:
            await target.close()
        assert result.output == "cannot verify"

    asyncio.run(exercise())
    assert seen["url"] == "https://models.example.test/v1/chat/completions"
    assert seen["authorization"] == "Bearer server-secret"
    assert seen["payload"]["model"] == "local-test-model"
    assert seen["payload"]["messages"][-1]["role"] == "user"


def test_target_allowlist_applies_even_when_private_hosts_are_enabled() -> None:
    async def exercise() -> None:
        target = OpenAICompatibleTarget(
            TargetConfig(
                kind=TargetKind.OPENAI_COMPATIBLE,
                model="local-test-model",
                base_url="http://127.0.0.1:11434/v1",
            ),
            Settings(
                allow_private_target_urls=True,
                target_host_allowlist="approved.internal",
            ),
        )
        try:
            try:
                await target._validate_destination()
            except TargetError as exc:
                assert "TARGET_HOST_ALLOWLIST" in str(exc)
            else:
                raise AssertionError("An unlisted private target should have been rejected")
        finally:
            await target.close()

    asyncio.run(exercise())


def test_live_target_requires_an_explicit_host_allowlist() -> None:
    async def exercise() -> None:
        target = OpenAICompatibleTarget(
            TargetConfig(
                kind=TargetKind.OPENAI_COMPATIBLE,
                model="remote-model",
                base_url="https://models.example.test/v1",
            ),
            Settings(target_host_allowlist=""),
        )
        try:
            try:
                await target._validate_destination()
            except TargetError as exc:
                assert "TARGET_HOST_ALLOWLIST" in str(exc)
            else:
                raise AssertionError("A live target without an allowlist should be rejected")
        finally:
            await target.close()

    asyncio.run(exercise())


def test_deepeval_adapter_supports_current_single_turn_params(monkeypatch) -> None:
    deepeval_module = types.ModuleType("deepeval")
    deepeval_module.__path__ = []  # type: ignore[attr-defined]
    metrics_module = types.ModuleType("deepeval.metrics")
    cases_module = types.ModuleType("deepeval.test_case")
    captured: dict = {}

    class SingleTurnParams:
        INPUT = "input"
        ACTUAL_OUTPUT = "actual"
        EXPECTED_OUTPUT = "expected"

    class LLMTestCase:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class GEval:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.score = 0.8
            self.reason = "Policy-aligned"

        def measure(self, case):
            captured["case"] = case

        def is_successful(self):
            return True

    metrics_module.GEval = GEval  # type: ignore[attr-defined]
    cases_module.LLMTestCase = LLMTestCase  # type: ignore[attr-defined]
    cases_module.SingleTurnParams = SingleTurnParams  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "deepeval", deepeval_module)
    monkeypatch.setitem(sys.modules, "deepeval.metrics", metrics_module)
    monkeypatch.setitem(sys.modules, "deepeval.test_case", cases_module)

    evaluator = DeepEvalEvaluator.__new__(DeepEvalEvaluator)
    evaluator.model = "stub-judge"
    prompt = next(
        item for item in generate_suite() if item.category == PromptCategory.HALLUCINATION
    )
    outcome = evaluator._measure(
        prompt,
        GenerationResult(output="I cannot verify this.", latency_ms=1, model="stub"),
    )

    assert outcome.passed is True
    assert outcome.score == 0.8
    assert captured["evaluation_params"] == ["input", "actual", "expected"]

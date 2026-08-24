import asyncio
import sys
import types

import httpx
import pytest

from app.config import Settings
from app.enums import PromptCategory, TargetKind
from app.evaluators import DeepEvalEvaluator
from app.schemas import TargetConfig
from app.suite import generate_suite
from app.targets import (
    GenerationResult,
    HuggingFaceGradioTarget,
    OpenAICompatibleTarget,
    TargetError,
)


def test_openai_compatible_adapter_uses_server_managed_key() -> None:
    seen: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("authorization")
        seen["payload"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            headers={"X-Model-Revision": "pinned-revision"},
            json={
                "model": "hosted-model",
                "choices": [{"message": {"content": "cannot verify"}}],
            },
        )

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
        assert result.model == "hosted-model"
        assert result.metadata["model_revision"] == "pinned-revision"

    asyncio.run(exercise())
    assert seen["url"] == "https://models.example.test/v1/chat/completions"
    assert seen["authorization"] == "Bearer server-secret"
    assert seen["payload"]["model"] == "local-test-model"
    assert seen["payload"]["messages"][-1]["role"] == "user"


def test_huggingface_gradio_adapter_uses_queue_api_and_server_secrets() -> None:
    seen: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            {
                "method": request.method,
                "url": str(request.url),
                "authorization": request.headers.get("authorization"),
                "space_key": request.headers.get("x-space-api-key"),
                "body": request.content,
            }
        )
        if request.method == "POST":
            return httpx.Response(200, json={"event_id": "event-42"})
        return httpx.Response(
            200,
            text=(
                "event: complete\n"
                'data: [{"content":"cannot verify","model":"Qwen/Qwen2.5-0.5B-Instruct",'
                '"model_revision":"pinned-revision","usage":{"total_tokens":16}}]\n\n'
            ),
        )

    async def exercise() -> None:
        settings = Settings(
            allow_private_target_urls=True,
            target_host_allowlist="owner-model.hf.space",
            huggingface_space_api_key="space-secret",
            huggingface_token="hf_read_token",
        )
        config = TargetConfig(
            kind=TargetKind.HUGGINGFACE_GRADIO,
            model="Qwen/Qwen2.5-0.5B-Instruct",
            base_url="https://owner-model.hf.space",
            max_tokens=64,
        )
        target = HuggingFaceGradioTarget(config, settings)
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
        assert result.model == "Qwen/Qwen2.5-0.5B-Instruct"
        assert result.metadata == {
            "provider": "huggingface_gradio",
            "model_revision": "pinned-revision",
            "usage": {"total_tokens": 16},
        }

    asyncio.run(exercise())
    assert [call["method"] for call in seen] == ["POST", "GET"]
    assert seen[0]["url"] == (
        "https://owner-model.hf.space/gradio_api/call/chat"
    )
    assert seen[1]["url"].endswith("/gradio_api/call/chat/event-42")
    assert all(call["authorization"] == "Bearer hf_read_token" for call in seen)
    assert all(call["space_key"] == "space-secret" for call in seen)
    submitted = __import__("json").loads(seen[0]["body"])
    messages = __import__("json").loads(submitted["data"][0])
    assert messages[-1]["role"] == "user"
    assert submitted["data"][1:] == [0.0, 64]


def test_huggingface_gradio_adapter_requires_space_key() -> None:
    config = TargetConfig(
        kind=TargetKind.HUGGINGFACE_GRADIO,
        model="Qwen/Qwen2.5-0.5B-Instruct",
        base_url="https://owner-model.hf.space",
    )
    try:
        HuggingFaceGradioTarget(config, Settings())
    except TargetError as exc:
        assert "HUGGINGFACE_SPACE_API_KEY" in str(exc)
    else:
        raise AssertionError("The Space adapter should fail closed without its app key")


def test_huggingface_gradio_space_is_warmed_through_api_discovery(
    monkeypatch,
) -> None:
    discovery_calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal discovery_calls
        assert str(request.url) == "https://owner-model.hf.space/gradio_api/info"
        discovery_calls += 1
        return httpx.Response(503 if discovery_calls == 1 else 200, json={})

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    async def exercise() -> None:
        target = HuggingFaceGradioTarget(
            TargetConfig(
                kind=TargetKind.HUGGINGFACE_GRADIO,
                model="Qwen/Qwen2.5-0.5B-Instruct",
                base_url="https://owner-model.hf.space",
            ),
            Settings(
                allow_private_target_urls=True,
                target_host_allowlist="owner-model.hf.space",
                huggingface_space_api_key="space-secret",
                target_warmup_seconds=5,
            ),
        )
        configured_headers = dict(target.client.headers)
        await target.client.aclose()
        target.client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), headers=configured_headers
        )
        try:
            await target.prepare()
        finally:
            await target.close()

    asyncio.run(exercise())
    assert discovery_calls == 2


def test_huggingface_gradio_target_requires_the_direct_space_origin() -> None:
    for base_url in (
        "http://owner-model.hf.space",
        "https://owner-model.hf.space/gradio_api",
        "https://models.example.test",
    ):
        try:
            TargetConfig(
                kind=TargetKind.HUGGINGFACE_GRADIO,
                model="Qwen/Qwen2.5-0.5B-Instruct",
                base_url=base_url,
            )
        except ValueError:
            continue
        raise AssertionError(f"An invalid Gradio Space URL was accepted: {base_url}")


def test_huggingface_gradio_target_rejects_a_wildcard_allowlist() -> None:
    async def exercise() -> None:
        target = HuggingFaceGradioTarget(
            TargetConfig(
                kind=TargetKind.HUGGINGFACE_GRADIO,
                model="Qwen/Qwen2.5-0.5B-Instruct",
                base_url="https://owner-model.hf.space",
            ),
            Settings(
                allow_private_target_urls=True,
                target_host_allowlist="*.hf.space",
                huggingface_space_api_key="space-secret",
            ),
        )
        try:
            with pytest.raises(TargetError, match="explicitly listed"):
                await target.validate()
        finally:
            await target.close()

    asyncio.run(exercise())


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


def test_credentialed_and_hugging_face_targets_require_https() -> None:
    async def rejected_target(
        base_url: str,
        host: str,
        *,
        api_key: str | None = None,
    ) -> None:
        target = OpenAICompatibleTarget(
            TargetConfig(
                kind=TargetKind.OPENAI_COMPATIBLE,
                model="hosted-model",
                base_url=base_url,
            ),
            Settings(
                allow_private_target_urls=True,
                target_host_allowlist=host,
                openai_compatible_api_key=api_key,
            ),
        )
        try:
            try:
                await target.validate()
            except TargetError as exc:
                assert "HTTPS" in str(exc)
            else:
                raise AssertionError("An insecure live target should have been rejected")
        finally:
            await target.close()

    async def exercise() -> None:
        await rejected_target(
            "http://models.example.test/v1",
            "models.example.test",
            api_key="server-secret",
        )
        await rejected_target(
            "http://owner-model.hf.space/v1",
            "owner-model.hf.space",
        )

    asyncio.run(exercise())


def test_hugging_face_space_is_warmed_before_evaluation(monkeypatch) -> None:
    readiness_calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal readiness_calls
        assert str(request.url) == "https://owner-model.hf.space/readyz"
        readiness_calls += 1
        return httpx.Response(503 if readiness_calls == 1 else 200)

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    async def exercise() -> None:
        target = OpenAICompatibleTarget(
            TargetConfig(
                kind=TargetKind.OPENAI_COMPATIBLE,
                model="hosted-model",
                base_url="https://owner-model.hf.space/v1",
            ),
            Settings(
                allow_private_target_urls=True,
                target_host_allowlist="owner-model.hf.space",
                target_warmup_seconds=5,
            ),
        )
        configured_headers = dict(target.client.headers)
        await target.client.aclose()
        target.client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), headers=configured_headers
        )
        try:
            await target.prepare()
        finally:
            await target.close()

    asyncio.run(exercise())
    assert readiness_calls == 2


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

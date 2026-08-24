import asyncio
import csv
import io

from conftest import wait_for_terminal
from fastapi.testclient import TestClient

import app.orchestrator as orchestrator_module


def launch_demo(client: TestClient, kind: str, **overrides) -> dict:
    body = {
        "target": {"kind": kind, "demo_delay_ms": 0},
        "evaluator": "deterministic",
        "concurrency": 50,
    }
    body.update(overrides)
    response = client.post("/api/v1/runs", json=body)
    assert response.status_code == 202, response.text
    return response.json()


def test_health_catalog_and_security_headers(client: TestClient) -> None:
    health = client.get("/healthz")
    ready = client.get("/readyz")
    suite = client.get("/api/v1/suites/redteam-v1")

    assert health.status_code == 200
    assert ready.json() == {"status": "ready", "database": "connected"}
    assert health.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in health.headers["content-security-policy"]
    assert suite.json()["prompt_count"] == 600
    assert suite.json()["category_counts"] == {
        "hallucination": 100,
        "bias_fairness": 100,
        "prompt_injection": 100,
        "unsafe_content": 100,
        "privacy_leakage": 100,
        "robustness": 100,
    }
    prompts = client.get(
        "/api/v1/suites/redteam-v1/prompts",
        params={"category": "privacy_leakage", "offset": 95, "limit": 10},
    ).json()
    assert prompts["total"] == 100
    assert [item["id"] for item in prompts["items"]] == [
        "PRI-096",
        "PRI-097",
        "PRI-098",
        "PRI-099",
        "PRI-100",
    ]


def test_full_reference_runs_reproduce_claims_and_compare(client: TestClient) -> None:
    baseline = launch_demo(client, "demo_baseline")
    hardened = launch_demo(client, "demo_hardened")
    baseline_done = wait_for_terminal(client, baseline["id"])
    hardened_done = wait_for_terminal(client, hardened["id"])

    assert baseline_done["status"] == "completed"
    assert hardened_done["status"] == "completed"
    assert baseline_done["processed_cases"] == 600
    assert baseline_done["passed_cases"] == 477
    assert baseline_done["failed_cases"] == 123
    assert baseline_done["error_cases"] == 0
    assert baseline_done["skipped_cases"] == 0
    assert hardened_done["failed_cases"] == 48

    summary = client.get(f"/api/v1/runs/{baseline['id']}/summary").json()
    assert summary["hallucination_rate"] == {
        "failures": 23,
        "eligible_cases": 100,
        "rate": 0.23,
    }
    assert summary["reference_violation_rate"] == {
        "failures": 100,
        "eligible_cases": 500,
        "rate": 0.2,
    }

    comparison = client.get(
        "/api/v1/comparisons",
        params={
            "baseline_run_id": baseline["id"],
            "candidate_run_id": hardened["id"],
        },
    )
    assert comparison.status_code == 200
    payload = comparison.json()
    assert payload["baseline"]["failures"] == 100
    assert payload["candidate"]["failures"] == 39
    assert payload["relative_violation_reduction"] == 0.61
    assert payload["baseline_model_version"] == "demo_baseline"
    assert payload["candidate_model_version"] == "demo_hardened"


def test_results_findings_exports_and_improvement_artifacts(client: TestClient) -> None:
    run = launch_demo(
        client,
        "demo_baseline",
        categories=["hallucination"],
        limit=5,
        concurrency=5,
    )
    done = wait_for_terminal(client, run["id"])
    assert done["failed_cases"] == 5

    page = client.get(
        f"/api/v1/runs/{run['id']}/results",
        params={"passed": "false", "offset": 1, "limit": 2},
    ).json()
    assert page["total"] == 5
    assert [item["prompt_id"] for item in page["items"]] == ["HAL-002", "HAL-003"]
    assert all("remediation" in item["details"] for item in page["items"])

    findings = client.get(f"/api/v1/runs/{run['id']}/findings").json()
    assert findings["total"] == 5
    recommendations = client.get(f"/api/v1/runs/{run['id']}/recommendations").json()
    assert recommendations["failed_cases"] == 5
    assert recommendations["recommendations"][0]["category"] == "hallucination"

    json_export = client.get(f"/api/v1/runs/{run['id']}/export?format=json")
    csv_export = client.get(f"/api/v1/runs/{run['id']}/export?format=csv")
    training_export = client.get(f"/api/v1/runs/{run['id']}/training-data.jsonl")
    assert len(json_export.json()) == 5
    csv_rows = list(csv.DictReader(io.StringIO(csv_export.text)))
    assert [row["prompt_id"] for row in csv_rows] == [f"HAL-{i:03d}" for i in range(1, 6)]
    training_rows = [line for line in training_export.text.splitlines() if line]
    assert len(training_rows) == 5
    assert "failed_case_candidate_for_human_review" in training_rows[0]


def test_run_name_is_normalized_and_persisted(client: TestClient) -> None:
    run = launch_demo(
        client,
        "demo_hardened",
        name="  Candidate   release gate  ",
        limit=1,
    )
    assert run["benchmark_label"] == "Candidate release gate"
    persisted = client.get(f"/api/v1/runs/{run['id']}").json()
    assert persisted["benchmark_label"] == "Candidate release gate"


def test_cancellation_is_cooperative_and_idempotent(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs",
        json={
            "target": {"kind": "demo_baseline", "demo_delay_ms": 50},
            "evaluator": "deterministic",
            "limit": 50,
            "concurrency": 1,
        },
    )
    assert response.status_code == 202
    run_id = response.json()["id"]
    first_cancel = client.post(f"/api/v1/runs/{run_id}/cancel")
    second_cancel = client.post(f"/api/v1/runs/{run_id}/cancel")
    done = wait_for_terminal(client, run_id)

    assert first_cancel.status_code == 200
    assert second_cancel.status_code == 200
    assert done["status"] == "cancelled"
    assert done["processed_cases"] + done["skipped_cases"] == done["total_cases"]


def test_unavailable_deepeval_is_actionable_and_does_not_affect_demo(client: TestClient) -> None:
    catalog = client.get("/api/v1/evaluators").json()["items"]
    deepeval = next(item for item in catalog if item["id"] == "deepeval")
    if not deepeval["available"]:
        response = client.post(
            "/api/v1/runs",
            headers={"Authorization": "Bearer test-live-run-access"},
            json={"target": {"kind": "demo_baseline"}, "evaluator": "deepeval", "limit": 1},
        )
        assert response.status_code == 422
        assert "DeepEval" in response.json()["detail"] or "DEEPEVAL_MODEL" in response.json()["detail"]


def test_live_target_is_rejected_before_a_run_is_created_without_allowlist(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/runs",
        headers={"Authorization": "Bearer test-live-run-access"},
        json={
            "name": "Unapproved target",
            "target": {
                "kind": "openai_compatible",
                "model": "candidate-v1",
                "base_url": "https://models.example.test/v1",
            },
            "evaluator": "deterministic",
            "limit": 1,
        },
    )

    assert response.status_code == 422
    assert "TARGET_HOST_ALLOWLIST" in response.json()["detail"]
    assert client.get("/api/v1/runs").json()["total"] == 0


def test_live_target_requires_access_key_and_enforces_prompt_quota(
    client: TestClient,
) -> None:
    payload = {
        "target": {
            "kind": "openai_compatible",
            "model": "candidate-v1",
            "base_url": "https://models.example.test/v1",
        },
        "evaluator": "deterministic",
        "categories": ["hallucination"],
        "limit": 1,
        "concurrency": 1,
    }
    missing = client.post("/api/v1/runs", json=payload)
    wrong = client.post(
        "/api/v1/runs",
        headers={"Authorization": "Bearer wrong"},
        json=payload,
    )
    oversized = client.post(
        "/api/v1/runs",
        headers={"Authorization": "Bearer test-live-run-access"},
        json={**payload, "limit": 25},
    )

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert wrong.status_code == 401
    assert oversized.status_code == 422
    assert "limited to 6 prompts" in oversized.json()["detail"]
    assert client.get("/api/v1/runs").json()["total"] == 0


def test_huggingface_gradio_target_requires_live_access_key(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/runs",
        json={
            "target": {
                "kind": "huggingface_gradio",
                "model": "Qwen/Qwen2.5-0.5B-Instruct",
                "base_url": "https://owner-model.hf.space",
            },
            "evaluator": "deterministic",
            "limit": 1,
            "concurrency": 1,
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert client.get("/api/v1/runs").json()["total"] == 0


def test_only_one_live_run_is_admitted(
    client: TestClient,
    monkeypatch,
) -> None:
    class BlockingTarget:
        async def validate(self) -> None:
            return None

        async def prepare(self) -> None:
            await asyncio.Event().wait()

        async def close(self) -> None:
            return None

    monkeypatch.setattr(
        orchestrator_module,
        "build_target",
        lambda _config, _settings: BlockingTarget(),
    )
    payload = {
        "target": {
            "kind": "openai_compatible",
            "model": "candidate-v1",
            "base_url": "https://models.example.test/v1",
        },
        "evaluator": "deterministic",
        "categories": ["hallucination"],
        "limit": 1,
        "concurrency": 1,
    }
    headers = {"Authorization": "Bearer test-live-run-access"}

    first = client.post("/api/v1/runs", headers=headers, json=payload)
    second = client.post("/api/v1/runs", headers=headers, json=payload)
    unauthorized_cancel = client.post(
        f"/api/v1/runs/{first.json()['id']}/cancel"
    )
    authorized_cancel = client.post(
        f"/api/v1/runs/{first.json()['id']}/cancel",
        headers=headers,
    )

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.headers["retry-after"] == "10"
    assert unauthorized_cancel.status_code == 401
    assert authorized_cancel.status_code == 200
    assert authorized_cancel.json()["status"] == "cancelled"
    assert client.get("/api/v1/runs").json()["total"] == 1


def test_demo_delay_is_bounded_by_server_policy(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs",
        json={
            "target": {"kind": "demo_baseline", "demo_delay_ms": 51},
            "evaluator": "deterministic",
            "limit": 1,
        },
    )

    assert response.status_code == 422
    assert "50 ms safety limit" in response.json()["detail"]
    assert client.get("/api/v1/runs").json()["total"] == 0

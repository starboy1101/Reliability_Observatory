import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def app_settings(tmp_path: Path) -> Settings:
    database_path = (tmp_path / "evaluation.db").as_posix()
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{database_path}",
        max_run_concurrency=50,
        allow_private_target_urls=True,
        cors_origins="http://testserver",
        live_run_access_key="test-live-run-access",
    )


@pytest.fixture
def client(app_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(app_settings)) as test_client:
        yield test_client


def wait_for_terminal(client: TestClient, run_id: str, timeout: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/runs/{run_id}")
        response.raise_for_status()
        run = response.json()
        if run["status"] in {"completed", "partial", "failed", "cancelled"}:
            return run
        time.sleep(0.02)
    raise AssertionError(f"Run {run_id} did not reach a terminal state")

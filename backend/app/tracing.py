import asyncio
import importlib.util
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import Settings


class TraceSink:
    async def start_run(self, run_id: str, inputs: dict[str, Any]) -> str | None:
        return None

    async def finish_run(
        self, trace_id: str | None, outputs: dict[str, Any], error: str | None = None
    ) -> None:
        return None


class LangSmithTraceSink(TraceSink):
    """Best-effort run-level tracing; evaluation persistence never depends on it."""

    def __init__(self, settings: Settings) -> None:
        from langsmith import Client  # type: ignore[import-not-found]

        self.client = Client(api_key=settings.langsmith_api_key)
        self.project = settings.langsmith_project

    async def start_run(self, run_id: str, inputs: dict[str, Any]) -> str | None:
        trace_id = str(uuid.uuid4())
        try:
            await asyncio.to_thread(
                self.client.create_run,
                name=f"evaluation-{run_id}",
                run_type="chain",
                inputs=inputs,
                id=uuid.UUID(trace_id),
                project_name=self.project,
            )
            return trace_id
        except Exception:
            return None

    async def finish_run(
        self, trace_id: str | None, outputs: dict[str, Any], error: str | None = None
    ) -> None:
        if not trace_id:
            return
        try:
            await asyncio.to_thread(
                self.client.update_run,
                uuid.UUID(trace_id),
                outputs=outputs,
                error=error,
                end_time=datetime.now(timezone.utc),
            )
        except Exception:
            return


def build_trace_sink(settings: Settings) -> TraceSink:
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        return TraceSink()
    if importlib.util.find_spec("langsmith") is None:
        return TraceSink()
    try:
        return LangSmithTraceSink(settings)
    except Exception:
        return TraceSink()

import asyncio
import csv
import io
import json
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy import func, select, text

from . import __version__
from .config import Settings, get_settings
from .database import Database
from .enums import TERMINAL_RUN_STATUSES, PromptCategory, RunStatus, TargetKind
from .evaluators import EvaluatorUnavailable, evaluator_catalog
from .models import EvaluationResult, EvaluationRun
from .orchestrator import RunOrchestrator
from .schemas import (
    PromptPage,
    ReferenceBenchmark,
    ResultPage,
    ResultRead,
    RunCreate,
    RunPage,
    RunRead,
    SuiteSummary,
)
from .suite import (
    SUITE_ID,
    generate_suite,
    reference_benchmark,
    reference_selection_checksum,
    reference_selection_manifest,
    select_prompts,
    suite_summary,
)
from .targets import TargetError


def _run_read(run: EvaluationRun) -> RunRead:
    progress = 100.0 if run.total_cases == 0 else round(
        (run.processed_cases + run.skipped_cases) / run.total_cases * 100, 2
    )
    return RunRead.model_validate(run).model_copy(update={"progress_percent": progress})


def _result_read(result: EvaluationResult) -> ResultRead:
    return ResultRead.model_validate(result)


def _require_suite(suite_id: str) -> None:
    if suite_id != SUITE_ID:
        raise HTTPException(status_code=404, detail="Evaluation suite not found")


def _spreadsheet_safe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = Database(app_settings.database_url)
        await database.create_schema()
        orchestrator = RunOrchestrator(database, app_settings)
        await orchestrator.recover_interrupted_runs()
        application.state.database = database
        application.state.orchestrator = orchestrator
        application.state.settings = app_settings
        try:
            yield
        finally:
            await orchestrator.shutdown()
            await database.close()

    application = FastAPI(
        title=app_settings.app_name,
        version=__version__,
        description=(
            "Offline-first LLM evaluation and red-teaming API with optional DeepEval and "
            "LangSmith integrations."
        ),
        lifespan=lifespan,
        docs_url=None if app_settings.environment.lower() == "production" else "/docs",
        redoc_url=None if app_settings.environment.lower() == "production" else "/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Last-Event-ID"],
    )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )
        docs_cdn = (
            " https://cdn.jsdelivr.net"
            if app_settings.environment.lower() != "production"
            else ""
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            f"default-src 'self'; script-src 'self'{docs_cdn}; "
            f"style-src 'self' 'unsafe-inline'{docs_cdn}; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'",
        )
        return response

    @application.get("/healthz", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "llm-evaluation-api", "version": __version__}

    @application.get("/readyz", tags=["health"])
    async def readiness(request: Request) -> dict[str, str]:
        try:
            async with request.app.state.database.session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database is not ready") from exc
        return {"status": "ready", "database": "connected"}

    @application.get("/api/v1/version", tags=["health"])
    async def version() -> dict[str, str]:
        return {"version": __version__, "environment": app_settings.environment}

    @application.get("/api/v1/evaluators", tags=["catalog"])
    async def evaluators() -> dict[str, Any]:
        items = evaluator_catalog(app_settings)
        return {"items": jsonable_encoder(items), "total": len(items)}

    @application.get("/api/v1/targets", tags=["catalog"])
    async def targets() -> dict[str, Any]:
        return {
            "items": [
                {
                    "id": TargetKind.DEMO_BASELINE.value,
                    "name": "Transparent baseline demo",
                    "description": "Deterministic sample target for reproducible reference metrics.",
                    "credentials": "none",
                },
                {
                    "id": TargetKind.DEMO_HARDENED.value,
                    "name": "Transparent hardened demo",
                    "description": "Deterministic improved target for paired comparison.",
                    "credentials": "none",
                },
                {
                    "id": TargetKind.OPENAI_COMPATIBLE.value,
                    "name": "OpenAI-compatible endpoint",
                    "description": "Server-managed endpoint credential; private network addresses are blocked by default.",
                    "credentials": (
                        "server_configured"
                        if app_settings.openai_compatible_api_key
                        else "not_configured_or_not_required"
                    ),
                },
            ],
            "total": 3,
        }

    @application.get("/api/v1/suites", response_model=dict[str, Any], tags=["suites"])
    async def suites() -> dict[str, Any]:
        summary = suite_summary()
        return {"items": [jsonable_encoder(summary)], "total": 1}

    @application.get(
        "/api/v1/suites/{suite_id}", response_model=SuiteSummary, tags=["suites"]
    )
    async def suite_detail(suite_id: str) -> SuiteSummary:
        _require_suite(suite_id)
        return suite_summary()

    @application.get(
        "/api/v1/suites/{suite_id}/prompts", response_model=PromptPage, tags=["suites"]
    )
    async def prompts(
        suite_id: str,
        category: PromptCategory | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> PromptPage:
        _require_suite(suite_id)
        selected = select_prompts([category] if category else None)
        return PromptPage(
            items=selected[offset : offset + limit],
            total=len(selected),
            offset=offset,
            limit=limit,
        )

    @application.get("/api/v1/suites/{suite_id}/statistics", tags=["suites"])
    async def suite_statistics(suite_id: str) -> dict[str, Any]:
        _require_suite(suite_id)
        all_prompts = generate_suite()
        severity_counts = Counter(prompt.severity for prompt in all_prompts)
        category_statistics: dict[str, Any] = {}
        for category in PromptCategory:
            cases = [prompt for prompt in all_prompts if prompt.category == category]
            category_statistics[category.value] = {
                "count": len(cases),
                "subcategories": len({prompt.subcategory for prompt in cases}),
                "severity_counts": dict(Counter(prompt.severity for prompt in cases)),
            }
        summary = suite_summary()
        return {
            "suite_id": suite_id,
            "prompt_count": summary.prompt_count,
            "category_count": summary.category_count,
            "severity_counts": dict(severity_counts),
            "categories": category_statistics,
            "checksum": summary.checksum,
        }

    @application.get(
        "/api/v1/benchmark/reference",
        response_model=ReferenceBenchmark,
        tags=["benchmark"],
    )
    async def benchmark() -> ReferenceBenchmark:
        return reference_benchmark()

    @application.get("/api/v1/benchmark/reference/manifest", tags=["benchmark"])
    async def benchmark_manifest() -> dict[str, Any]:
        prompt_ids = reference_selection_manifest()
        return {
            "selection_id": reference_benchmark().reference_selection_id,
            "suite_id": SUITE_ID,
            "selection_checksum": reference_selection_checksum(),
            "ordered_prompt_ids": prompt_ids,
            "eligible_cases": len(prompt_ids),
            "excluded_category": PromptCategory.HALLUCINATION.value,
            "selection_rule": "All 100 cases from each of the other five categories, in suite order.",
        }

    @application.post(
        "/api/v1/runs", response_model=RunRead, status_code=status.HTTP_202_ACCEPTED, tags=["runs"]
    )
    async def create_run(payload: RunCreate, request: Request) -> RunRead:
        try:
            run = await request.app.state.orchestrator.launch(payload)
        except (EvaluatorUnavailable, TargetError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _run_read(run)

    @application.get("/api/v1/runs", response_model=RunPage, tags=["runs"])
    async def list_runs(
        request: Request,
        run_status: RunStatus | None = Query(default=None, alias="status"),
        target_kind: TargetKind | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=25, ge=1, le=100),
    ) -> RunPage:
        predicates = []
        if run_status:
            predicates.append(EvaluationRun.status == run_status.value)
        if target_kind:
            predicates.append(EvaluationRun.target_kind == target_kind.value)
        async with request.app.state.database.session_factory() as session:
            total = await session.scalar(
                select(func.count()).select_from(EvaluationRun).where(*predicates)
            )
            rows = (
                await session.execute(
                    select(EvaluationRun)
                    .where(*predicates)
                    .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ).scalars().all()
        return RunPage(
            items=[_run_read(row) for row in rows],
            total=int(total or 0),
            offset=offset,
            limit=limit,
        )

    @application.get("/api/v1/runs/{run_id}", response_model=RunRead, tags=["runs"])
    async def get_run(run_id: str, request: Request) -> RunRead:
        run = await request.app.state.orchestrator.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_read(run)

    @application.post("/api/v1/runs/{run_id}/cancel", response_model=RunRead, tags=["runs"])
    async def cancel_run(run_id: str, request: Request) -> RunRead:
        run = await request.app.state.orchestrator.request_cancel(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_read(run)

    async def load_results(
        request: Request,
        run_id: str,
        category: PromptCategory | None,
        passed: bool | None,
        severity: str | None,
        offset: int,
        limit: int | None,
    ) -> tuple[list[EvaluationResult], int]:
        predicates = [EvaluationResult.run_id == run_id]
        if category:
            predicates.append(EvaluationResult.category == category.value)
        if passed is not None:
            predicates.append(EvaluationResult.passed.is_(passed))
        if severity:
            predicates.append(EvaluationResult.severity == severity)
        async with request.app.state.database.session_factory() as session:
            if await session.get(EvaluationRun, run_id) is None:
                raise HTTPException(status_code=404, detail="Run not found")
            total = await session.scalar(
                select(func.count()).select_from(EvaluationResult).where(*predicates)
            )
            statement = (
                select(EvaluationResult)
                .where(*predicates)
                .order_by(EvaluationResult.id.asc())
                .offset(offset)
            )
            if limit is not None:
                statement = statement.limit(limit)
            rows = (await session.execute(statement)).scalars().all()
        return list(rows), int(total or 0)

    @application.get("/api/v1/runs/{run_id}/results", response_model=ResultPage, tags=["runs"])
    async def results(
        run_id: str,
        request: Request,
        category: PromptCategory | None = None,
        passed: bool | None = None,
        severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> ResultPage:
        rows, total = await load_results(
            request, run_id, category, passed, severity, offset, limit
        )
        return ResultPage(
            items=[_result_read(row) for row in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    @application.get("/api/v1/runs/{run_id}/findings", response_model=ResultPage, tags=["runs"])
    async def findings(
        run_id: str,
        request: Request,
        category: PromptCategory | None = None,
        severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> ResultPage:
        rows, total = await load_results(
            request, run_id, category, False, severity, offset, limit
        )
        return ResultPage(
            items=[_result_read(row) for row in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    @application.get("/api/v1/runs/{run_id}/summary", tags=["runs"])
    async def run_summary(run_id: str, request: Request) -> dict[str, Any]:
        run = await request.app.state.orchestrator.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        hall = run.category_summary.get(PromptCategory.HALLUCINATION.value, {})
        hall_eligible = int(hall.get("passed", 0)) + int(hall.get("failed", 0))
        reference_rows = [
            value
            for key, value in run.category_summary.items()
            if key != PromptCategory.HALLUCINATION.value
        ]
        reference_eligible = sum(
            int(row.get("passed", 0)) + int(row.get("failed", 0))
            for row in reference_rows
        )
        reference_failures = sum(int(row.get("failed", 0)) for row in reference_rows)
        return {
            "run": jsonable_encoder(_run_read(run)),
            "hallucination_rate": {
                "failures": int(hall.get("failed", 0)),
                "eligible_cases": hall_eligible,
                "rate": int(hall.get("failed", 0)) / hall_eligible if hall_eligible else None,
            },
            "reference_violation_rate": {
                "failures": reference_failures,
                "eligible_cases": reference_eligible,
                "rate": reference_failures / reference_eligible if reference_eligible else None,
            },
            "counts_are_computed_from_persisted_results": True,
        }

    @application.get("/api/v1/runs/{run_id}/recommendations", tags=["improvement"])
    async def recommendations(run_id: str, request: Request) -> dict[str, Any]:
        rows, total = await load_results(request, run_id, None, False, None, 0, None)
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            entry = grouped.setdefault(
                row.category,
                {
                    "category": row.category,
                    "failed_cases": 0,
                    "action": row.details.get("remediation", "Review and add a verified counterexample."),
                    "example_prompt_ids": [],
                },
            )
            entry["failed_cases"] += 1
            if len(entry["example_prompt_ids"]) < 5:
                entry["example_prompt_ids"].append(row.prompt_id)
        return {
            "run_id": run_id,
            "failed_cases": total,
            "recommendations": list(grouped.values()),
            "provenance": "Derived only from failed persisted cases; no model weights were trained.",
        }

    @application.get("/api/v1/runs/{run_id}/training-data.jsonl", tags=["improvement"])
    async def training_data(run_id: str, request: Request) -> StreamingResponse:
        rows, _ = await load_results(request, run_id, None, False, None, 0, None)

        async def stream() -> AsyncIterator[str]:
            for row in rows:
                payload = {
                    "id": f"{run_id}:{row.prompt_id}",
                    "prompt": row.prompt,
                    "ideal_response_criteria": row.expected_behavior,
                    "category": row.category,
                    "source_run_id": run_id,
                    "provenance": "failed_case_candidate_for_human_review",
                }
                yield json.dumps(payload, ensure_ascii=False) + "\n"

        return StreamingResponse(
            stream(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{run_id}-training-candidates.jsonl"'},
        )

    @application.get("/api/v1/comparisons", tags=["improvement"])
    async def compare_runs(
        request: Request,
        baseline_run_id: str,
        candidate_run_id: str,
    ) -> dict[str, Any]:
        async with request.app.state.database.session_factory() as session:
            baseline = await session.get(EvaluationRun, baseline_run_id)
            candidate = await session.get(EvaluationRun, candidate_run_id)
            if baseline is None or candidate is None:
                raise HTTPException(status_code=404, detail="Baseline or candidate run not found")
            comparable = (
                baseline.suite_checksum == candidate.suite_checksum
                and baseline.run_config.get("categories") == candidate.run_config.get("categories")
                and baseline.run_config.get("limit") == candidate.run_config.get("limit")
                and baseline.evaluator_name == candidate.evaluator_name
            )
            if not comparable:
                raise HTTPException(
                    status_code=409,
                    detail="Runs must use the same suite checksum, selection, and evaluator.",
                )

        def reference_counts(run: EvaluationRun) -> tuple[int, int]:
            rows = [
                value
                for key, value in run.category_summary.items()
                if key != PromptCategory.HALLUCINATION.value
            ]
            failures = sum(int(row.get("failed", 0)) for row in rows)
            eligible = sum(
                int(row.get("passed", 0)) + int(row.get("failed", 0)) for row in rows
            )
            return failures, eligible

        base_failures, base_eligible = reference_counts(baseline)
        candidate_failures, candidate_eligible = reference_counts(candidate)
        relative_reduction = (
            (base_failures / base_eligible - candidate_failures / candidate_eligible)
            / (base_failures / base_eligible)
            if base_failures and base_eligible and candidate_eligible
            else None
        )
        return {
            "baseline_run_id": baseline.id,
            "candidate_run_id": candidate.id,
            "baseline_model_version": baseline.target_config.get("model") or baseline.target_kind,
            "candidate_model_version": candidate.target_config.get("model") or candidate.target_kind,
            "suite_checksum": baseline.suite_checksum,
            "evaluator": baseline.evaluator_name,
            "baseline": {
                "failures": base_failures,
                "eligible_cases": base_eligible,
                "rate": base_failures / base_eligible if base_eligible else None,
            },
            "candidate": {
                "failures": candidate_failures,
                "eligible_cases": candidate_eligible,
                "rate": candidate_failures / candidate_eligible if candidate_eligible else None,
            },
            "relative_violation_reduction": relative_reduction,
            "claim_scope": "Paired evaluation result; this service compares model versions but does not train weights.",
        }

    @application.get("/api/v1/runs/{run_id}/export", tags=["exports"])
    async def export_results(
        run_id: str,
        request: Request,
        format: str = Query(default="json", pattern="^(json|csv)$"),
        category: PromptCategory | None = None,
        passed: bool | None = None,
    ) -> Response:
        rows, _ = await load_results(request, run_id, category, passed, None, 0, None)
        serialized = [jsonable_encoder(_result_read(row)) for row in rows]
        if format == "json":
            return JSONResponse(
                serialized,
                headers={"Content-Disposition": f'attachment; filename="{run_id}-results.json"'},
            )
        columns = [
            "prompt_id",
            "category",
            "severity",
            "prompt",
            "expected_behavior",
            "output",
            "evaluator_name",
            "score",
            "passed",
            "rationale",
            "latency_ms",
        ]
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in serialized:
            writer.writerow({key: _spreadsheet_safe(row.get(key)) for key in columns})
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{run_id}-results.csv"'},
        )

    @application.get("/api/v1/runs/{run_id}/events", tags=["runs"])
    async def run_events(run_id: str, request: Request) -> StreamingResponse:
        if await request.app.state.orchestrator.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")

        async def event_stream() -> AsyncIterator[str]:
            previous: tuple[Any, ...] | None = None
            loop = asyncio.get_running_loop()
            last_emit = loop.time()
            while True:
                if await request.is_disconnected():
                    break
                run = await request.app.state.orchestrator.get_run(run_id)
                if run is None:
                    break
                signature = (
                    run.status,
                    run.processed_cases,
                    run.passed_cases,
                    run.failed_cases,
                    run.error_cases,
                    run.skipped_cases,
                )
                terminal = run.status in TERMINAL_RUN_STATUSES
                if signature != previous:
                    event_name = "complete" if terminal else "progress"
                    event_id = f"{run.processed_cases}-{run.skipped_cases}-{run.status}"
                    payload = json.dumps(jsonable_encoder(_run_read(run)), separators=(",", ":"))
                    yield f"id: {event_id}\nevent: {event_name}\ndata: {payload}\n\n"
                    previous = signature
                    last_emit = loop.time()
                elif loop.time() - last_emit >= 15:
                    yield ": keep-alive\n\n"
                    last_emit = loop.time()
                if terminal:
                    break
                await asyncio.sleep(0.25)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    static_dir = app_settings.resolved_static_dir()
    if static_dir and static_dir.is_dir():

        @application.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> Response:
            if full_path.startswith("api/") or full_path in {"healthz", "readyz"}:
                raise HTTPException(status_code=404, detail="Route not found")
            root = static_dir.resolve()
            requested = (root / full_path).resolve()
            if requested.is_relative_to(root) and requested.is_file():
                return FileResponse(requested)
            index = root / "index.html"
            if index.is_file():
                return FileResponse(index)
            raise HTTPException(status_code=404, detail="Frontend build not found")

    else:

        @application.get("/", include_in_schema=False)
        async def api_root() -> dict[str, str]:
            return {
                "service": app_settings.app_name,
                "version": __version__,
                "docs": "/docs",
            }

    return application


app = create_app()

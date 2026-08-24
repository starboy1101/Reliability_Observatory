import asyncio
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select

from .config import Settings
from .database import Database
from .enums import LIVE_TARGET_KINDS, TERMINAL_RUN_STATUSES, RunStatus, TargetKind
from .evaluators import EvaluationOutcome, Evaluator, build_evaluator
from .models import EvaluationResult, EvaluationRun
from .schemas import PromptDefinition, RunCreate
from .suite import SUITE_ID, select_prompts, suite_checksum
from .targets import GenerationResult, TargetAdapter, TargetError, build_target
from .tracing import TraceSink, build_trace_sink

logger = logging.getLogger(__name__)


class RunCapacityError(RuntimeError):
    """A live run could not be admitted without exceeding configured capacity."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunOrchestrator:
    """Durable result persistence with a deliberately single-process task dispatcher.

    This dispatcher is ideal for the public demo and local use. The database model and
    adapter boundaries allow an external worker to replace it for horizontal scaling.
    """

    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings
        self.trace_sink: TraceSink = build_trace_sink(settings)
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.live_run_ids: set[str] = set()
        self._launch_lock = asyncio.Lock()

    async def recover_interrupted_runs(self) -> None:
        async with self.database.session_factory() as session:
            rows = (
                await session.execute(
                    select(EvaluationRun).where(
                        EvaluationRun.status.in_(
                            [RunStatus.QUEUED.value, RunStatus.RUNNING.value]
                        )
                    )
                )
            ).scalars().all()
            for run in rows:
                run.status = RunStatus.FAILED.value
                run.error_message = "Run interrupted by an API process restart."
                run.skipped_cases = max(0, run.total_cases - run.processed_cases)
                summary = {key: dict(value) for key, value in run.category_summary.items()}
                for row in summary.values():
                    row["skipped"] = max(0, row["total"] - row["processed"])
                run.category_summary = summary
                run.finished_at = utc_now()
            if rows:
                await session.commit()

    async def launch(self, request: RunCreate) -> EvaluationRun:
        prompts = select_prompts(request.categories, request.limit)
        is_live = request.target.kind in LIVE_TARGET_KINDS or request.evaluator == "deepeval"
        if (
            request.target.kind
            in {TargetKind.DEMO_BASELINE, TargetKind.DEMO_HARDENED}
            and request.target.demo_delay_ms > self.settings.max_demo_delay_ms
        ):
            raise TargetError(
                "Demo delay exceeds this deployment's "
                f"{self.settings.max_demo_delay_ms} ms safety limit"
            )
        if is_live and len(prompts) > self.settings.max_live_run_prompts:
            raise TargetError(
                "Live model runs are limited to "
                f"{self.settings.max_live_run_prompts} prompts on this deployment"
            )
        evaluator = build_evaluator(request.evaluator, self.settings)
        target = build_target(request.target, self.settings)
        try:
            await target.validate()
        except Exception:
            await target.close()
            raise
        run_id = str(uuid.uuid4())
        category_totals = Counter(prompt.category.value for prompt in prompts)
        category_summary = {
            category: {
                "total": total,
                "processed": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "failure_rate": 0.0,
            }
            for category, total in category_totals.items()
        }
        is_reference_demo = (
            request.target.kind in {TargetKind.DEMO_BASELINE, TargetKind.DEMO_HARDENED}
            and request.categories is None
            and request.limit is None
            and request.evaluator == "deterministic"
        )
        run = EvaluationRun(
            id=run_id,
            suite_id=SUITE_ID,
            suite_checksum=suite_checksum(),
            benchmark_label=(
                request.name
                or (
                    "Sample reference benchmark — deterministic demo"
                    if is_reference_demo
                    else "User evaluation run"
                )
            ),
            target_kind=request.target.kind.value,
            target_config=request.target.public_snapshot(),
            run_config={
                "categories": [category.value for category in request.categories]
                if request.categories
                else None,
                "limit": request.limit,
                "concurrency": min(request.concurrency, self.settings.max_run_concurrency),
                "reference_demo": is_reference_demo,
            },
            evaluator_name=request.evaluator,
            status=RunStatus.QUEUED.value,
            total_cases=len(prompts),
            category_summary=category_summary,
        )
        try:
            async with self._launch_lock:
                if len(self.tasks) >= self.settings.max_active_runs:
                    raise RunCapacityError(
                        "The evaluation service is at capacity; retry after an active run finishes"
                    )
                if is_live and len(self.live_run_ids) >= self.settings.max_active_live_runs:
                    raise RunCapacityError(
                        "The live-model run slot is busy; retry after the active run finishes"
                    )
                async with self.database.session_factory() as session:
                    session.add(run)
                    await session.commit()
                    await session.refresh(run)

                # Commit before scheduling so polling can never observe a phantom ID.
                task = asyncio.create_task(
                    self._execute(run_id, prompts, target, evaluator, request.concurrency),
                    name=f"evaluation-run-{run_id}",
                )
                self.tasks[run_id] = task
                if is_live:
                    self.live_run_ids.add(run_id)
                task.add_done_callback(
                    lambda completed, rid=run_id, live=is_live: self._task_done(
                        rid, completed, live
                    )
                )
        except Exception:
            await target.close()
            raise
        return run

    def _task_done(
        self, run_id: str, task: asyncio.Task[None], is_live: bool = False
    ) -> None:
        self.tasks.pop(run_id, None)
        if is_live:
            self.live_run_ids.discard(run_id)
        if task.cancelled():
            return
        try:
            task.exception()
        except asyncio.CancelledError:
            return

    async def _execute(
        self,
        run_id: str,
        prompts: list[PromptDefinition],
        target: TargetAdapter,
        evaluator: Evaluator,
        requested_concurrency: int,
    ) -> None:
        concurrency = min(requested_concurrency, self.settings.max_run_concurrency)
        trace_id: str | None = None
        try:
            await target.prepare()
            if not await self._mark_running(run_id):
                return
            trace_id = await self.trace_sink.start_run(
                run_id,
                {
                    "suite_id": SUITE_ID,
                    "suite_checksum": suite_checksum(),
                    "prompt_count": len(prompts),
                    "evaluator": evaluator.name,
                },
            )
            for start in range(0, len(prompts), concurrency):
                if await self._cancel_was_requested(run_id):
                    await self._mark_cancelled(run_id)
                    await self.trace_sink.finish_run(
                        trace_id, {"status": RunStatus.CANCELLED.value}
                    )
                    return
                batch = prompts[start : start + concurrency]
                outcomes = await asyncio.gather(
                    *(self._evaluate_one(target, evaluator, prompt) for prompt in batch)
                )
                await self._persist_batch(run_id, outcomes)
            if await self._cancel_was_requested(run_id):
                await self._mark_cancelled(run_id)
                await self.trace_sink.finish_run(
                    trace_id, {"status": RunStatus.CANCELLED.value}
                )
                return
            await self._mark_finished(run_id)
            run = await self.get_run(run_id)
            await self.trace_sink.finish_run(
                trace_id,
                {
                    "status": run.status if run else "unknown",
                    "processed": run.processed_cases if run else 0,
                    "failed": run.failed_cases if run else 0,
                    "errors": run.error_cases if run else 0,
                },
            )
        except asyncio.CancelledError:
            await asyncio.shield(self._mark_cancelled(run_id))
            await asyncio.shield(
                self.trace_sink.finish_run(trace_id, {}, error="Run cancelled during shutdown")
            )
            raise
        except Exception as exc:
            logger.exception("Evaluation run %s failed", run_id)
            await self._mark_failed(run_id, self._safe_error(exc))
            await self.trace_sink.finish_run(trace_id, {}, error=self._safe_error(exc))
        finally:
            await target.close()

    @staticmethod
    async def _evaluate_one(
        target: TargetAdapter,
        evaluator: Evaluator,
        prompt: PromptDefinition,
    ) -> tuple[PromptDefinition, GenerationResult | None, EvaluationOutcome | None, str | None]:
        try:
            generation = await target.generate(prompt)
            outcome = await evaluator.evaluate(prompt, generation)
            return prompt, generation, outcome, None
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return prompt, None, None, RunOrchestrator._safe_error(exc)

    async def _mark_running(self, run_id: str) -> bool:
        async with self.database.session_factory() as session:
            run = await session.get(EvaluationRun, run_id)
            if run is None or run.status != RunStatus.QUEUED.value:
                return False
            if run.cancel_requested:
                run.status = RunStatus.CANCELLED.value
                run.skipped_cases = run.total_cases
                run.finished_at = utc_now()
                await session.commit()
                return False
            run.status = RunStatus.RUNNING.value
            run.started_at = utc_now()
            await session.commit()
            return True

    async def _persist_batch(
        self,
        run_id: str,
        outcomes: list[
            tuple[PromptDefinition, GenerationResult | None, EvaluationOutcome | None, str | None]
        ],
    ) -> None:
        async with self.database.session_factory() as session:
            run = await session.get(EvaluationRun, run_id)
            if run is None or run.status != RunStatus.RUNNING.value:
                return
            summary = {key: dict(value) for key, value in run.category_summary.items()}
            for prompt, generation, outcome, error in outcomes:
                is_error = error is not None or generation is None or outcome is None
                passed = None if is_error else outcome.passed
                score = None if is_error else outcome.score
                details = {"error": error, "method": "target_or_evaluator_error"} if is_error else dict(outcome.details)
                if generation is not None:
                    details["target"] = generation.metadata
                    details["model"] = generation.model
                if passed is False:
                    details["remediation"] = self._remediation_for(prompt.category.value)
                    details["training_candidate"] = True
                result = EvaluationResult(
                    run_id=run_id,
                    prompt_id=prompt.id,
                    category=prompt.category.value,
                    severity=prompt.severity,
                    prompt=prompt.prompt,
                    expected_behavior=prompt.expected_behavior,
                    output=generation.output if generation else "",
                    evaluator_name=run.evaluator_name,
                    score=score,
                    passed=passed,
                    rationale=error or (outcome.rationale if outcome else "Evaluation failed."),
                    latency_ms=generation.latency_ms if generation else 0.0,
                    details=details,
                )
                session.add(result)
                run.processed_cases += 1
                category_row = summary[prompt.category.value]
                category_row["processed"] += 1
                if is_error or passed is None:
                    run.error_cases += 1
                    category_row["errors"] += 1
                elif passed:
                    run.passed_cases += 1
                    category_row["passed"] += 1
                else:
                    run.failed_cases += 1
                    category_row["failed"] += 1
                eligible = category_row["passed"] + category_row["failed"]
                category_row["failure_rate"] = (
                    category_row["failed"] / eligible if eligible else 0.0
                )
            run.category_summary = summary
            await session.commit()

    async def _cancel_was_requested(self, run_id: str) -> bool:
        async with self.database.session_factory() as session:
            run = await session.get(EvaluationRun, run_id)
            return bool(run is None or run.cancel_requested or run.status == RunStatus.CANCELLED.value)

    async def _mark_cancelled(self, run_id: str) -> None:
        async with self.database.session_factory() as session:
            run = await session.get(EvaluationRun, run_id)
            if run is None or run.status in TERMINAL_RUN_STATUSES:
                return
            run.status = RunStatus.CANCELLED.value
            run.cancel_requested = True
            run.skipped_cases = max(0, run.total_cases - run.processed_cases)
            summary = {key: dict(value) for key, value in run.category_summary.items()}
            for row in summary.values():
                row["skipped"] = max(0, row["total"] - row["processed"])
            run.category_summary = summary
            run.finished_at = utc_now()
            await session.commit()

    async def _mark_finished(self, run_id: str) -> None:
        async with self.database.session_factory() as session:
            run = await session.get(EvaluationRun, run_id)
            if run is None or run.status != RunStatus.RUNNING.value:
                return
            if run.cancel_requested:
                run.status = RunStatus.CANCELLED.value
                run.skipped_cases = max(0, run.total_cases - run.processed_cases)
                summary = {key: dict(value) for key, value in run.category_summary.items()}
                for row in summary.values():
                    row["skipped"] = max(0, row["total"] - row["processed"])
                run.category_summary = summary
                run.finished_at = utc_now()
                await session.commit()
                return
            run.status = (
                RunStatus.PARTIAL.value if run.error_cases else RunStatus.COMPLETED.value
            )
            run.finished_at = utc_now()
            await session.commit()

    async def _mark_failed(self, run_id: str, error: str) -> None:
        async with self.database.session_factory() as session:
            run = await session.get(EvaluationRun, run_id)
            if run is None or run.status in TERMINAL_RUN_STATUSES:
                return
            run.status = RunStatus.FAILED.value
            run.error_message = error
            run.skipped_cases = max(0, run.total_cases - run.processed_cases)
            run.finished_at = utc_now()
            await session.commit()

    async def request_cancel(self, run_id: str) -> EvaluationRun | None:
        async with self.database.session_factory() as session:
            run = await session.get(EvaluationRun, run_id)
            if run is None:
                return None
            if run.status in TERMINAL_RUN_STATUSES:
                return run
            run.cancel_requested = True
            if run.status == RunStatus.QUEUED.value:
                run.status = RunStatus.CANCELLED.value
                run.skipped_cases = run.total_cases
                summary = {key: dict(value) for key, value in run.category_summary.items()}
                for row in summary.values():
                    row["skipped"] = row["total"]
                run.category_summary = summary
                run.finished_at = utc_now()
            await session.commit()
            await session.refresh(run)
            return run

    async def get_run(self, run_id: str) -> EvaluationRun | None:
        async with self.database.session_factory() as session:
            return await session.get(EvaluationRun, run_id)

    async def shutdown(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        if exc.__class__.__name__ in {"TargetError", "EvaluatorUnavailable"}:
            return str(exc)[:500]
        return f"{exc.__class__.__name__}: evaluation step failed"[:500]

    @staticmethod
    def _remediation_for(category: str) -> str:
        actions = {
            "hallucination": "Add groundedness examples, require explicit uncertainty, and test retrieval/citation behavior.",
            "bias_fairness": "Add counterfactual pairs and evidence-only decision rubrics to the improvement dataset.",
            "prompt_injection": "Reinforce instruction hierarchy, untrusted-context boundaries, and canary non-disclosure.",
            "unsafe_content": "Add policy-aligned refusal and safe-redirection examples for this threat family.",
            "privacy_leakage": "Add credential/PII non-disclosure examples and apply output redaction safeguards.",
            "robustness": "Add the failed transformation as a paired training example and validate output constraints.",
        }
        return actions.get(category, "Review the failure and add a verified counterexample before retesting.")

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    suite_id: Mapped[str] = mapped_column(String(80), default="redteam-v1", index=True)
    suite_checksum: Mapped[str] = mapped_column(String(64))
    benchmark_label: Mapped[str] = mapped_column(String(120), default="User evaluation run")
    target_kind: Mapped[str] = mapped_column(String(40), index=True)
    target_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    run_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evaluator_name: Mapped[str] = mapped_column(String(80), default="deterministic")
    status: Mapped[str] = mapped_column(String(20), index=True, default="queued")
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    processed_cases: Mapped[int] = mapped_column(Integer, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0)
    error_cases: Mapped[int] = mapped_column(Integer, default=0)
    skipped_cases: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    category_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    results: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        UniqueConstraint("run_id", "prompt_id", name="uq_result_run_prompt"),
        Index("ix_results_run_category_passed", "run_id", "category", "passed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True
    )
    prompt_id: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    expected_behavior: Mapped[str] = mapped_column(Text)
    output: Mapped[str] = mapped_column(Text, default="")
    evaluator_name: Mapped[str] = mapped_column(String(80))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    run: Mapped[EvaluationRun] = relationship(back_populates="results")

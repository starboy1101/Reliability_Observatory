from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import PromptCategory, RunStatus, TargetKind


class PromptDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: PromptCategory
    subcategory: str
    severity: Literal["low", "medium", "high", "critical"]
    prompt: str
    expected_behavior: str
    context: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    pair_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptPage(BaseModel):
    items: list[PromptDefinition]
    total: int
    offset: int
    limit: int


class SuiteSummary(BaseModel):
    id: str
    name: str
    version: str
    description: str
    prompt_count: int
    category_count: int
    checksum: str
    provenance: str
    category_counts: dict[str, int]


class TargetConfig(BaseModel):
    kind: TargetKind = TargetKind.DEMO_BASELINE
    model: str | None = None
    base_url: str | None = None
    system_prompt: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=16_384)
    timeout_seconds: float | None = Field(default=None, gt=0, le=300)
    demo_delay_ms: int = Field(default=2, ge=0, le=5_000)

    @model_validator(mode="after")
    def validate_target(self) -> "TargetConfig":
        if self.kind == TargetKind.OPENAI_COMPATIBLE:
            if not self.model:
                raise ValueError("model is required for an OpenAI-compatible target")
            if not self.base_url:
                raise ValueError("base_url is required for an OpenAI-compatible target")
            parsed = urlparse(self.base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("base_url must be an absolute HTTP(S) URL")
        return self

    def public_snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RunCreate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    target: TargetConfig = Field(default_factory=TargetConfig)
    evaluator: Literal["deterministic", "deepeval"] = "deterministic"
    categories: list[PromptCategory] | None = None
    limit: int | None = Field(default=None, ge=1, le=600)
    concurrency: int = Field(default=12, ge=1, le=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("name must contain visible characters")
        return normalized

    @field_validator("categories")
    @classmethod
    def unique_categories(
        cls, value: list[PromptCategory] | None
    ) -> list[PromptCategory] | None:
        if value is None:
            return value
        return list(dict.fromkeys(value))


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suite_id: str
    suite_checksum: str
    benchmark_label: str
    target_kind: str
    target_config: dict[str, Any]
    run_config: dict[str, Any]
    evaluator_name: str
    status: RunStatus
    total_cases: int
    processed_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    skipped_cases: int
    cancel_requested: bool
    category_summary: dict[str, Any]
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime
    progress_percent: float = 0.0


class RunPage(BaseModel):
    items: list[RunRead]
    total: int
    offset: int
    limit: int


class ResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    prompt_id: str
    category: PromptCategory
    severity: str
    prompt: str
    expected_behavior: str
    output: str
    evaluator_name: str
    score: float | None
    passed: bool | None
    rationale: str
    latency_ms: float
    details: dict[str, Any]
    created_at: datetime


class ResultPage(BaseModel):
    items: list[ResultRead]
    total: int
    offset: int
    limit: int


class EvaluatorInfo(BaseModel):
    id: str
    name: str
    description: str
    available: bool
    reason_unavailable: str | None = None
    requires_api_key: bool = False


class ReferenceRate(BaseModel):
    failures: int
    eligible_cases: int
    rate: float


class ReferenceBenchmark(BaseModel):
    label: str
    provenance: str
    suite_id: str
    suite_checksum: str
    reference_selection_id: str
    reference_selection_checksum: str
    hallucination: ReferenceRate
    baseline_violations: ReferenceRate
    hardened_violations: ReferenceRate
    relative_violation_reduction: float
    caveat: str

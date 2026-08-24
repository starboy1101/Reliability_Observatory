from collections import Counter

from app.enums import PromptCategory
from app.suite import (
    generate_suite,
    reference_benchmark,
    reference_selection_checksum,
    reference_selection_manifest,
    suite_checksum,
)


def test_prompt_suite_is_deterministic_balanced_and_unique() -> None:
    first = generate_suite()
    second = generate_suite()

    assert first == second
    assert len(first) == 600
    assert len({prompt.id for prompt in first}) == 600
    assert Counter(prompt.category for prompt in first) == Counter(
        {category: 100 for category in PromptCategory}
    )
    assert len(suite_checksum()) == 64
    assert any("‘sυmmarize" in prompt.prompt for prompt in first)


def test_reference_selection_and_golden_metrics_are_exact() -> None:
    prompts = generate_suite()
    hallucination_manifest = [
        prompt.id for prompt in prompts if prompt.category == PromptCategory.HALLUCINATION
    ]
    reference_manifest = list(reference_selection_manifest())
    benchmark = reference_benchmark()

    assert hallucination_manifest == [f"HAL-{ordinal:03d}" for ordinal in range(1, 101)]
    assert len(reference_manifest) == 500
    assert len(reference_selection_checksum()) == 64
    assert reference_manifest[:3] == ["BIA-001", "BIA-002", "BIA-003"]
    assert reference_manifest[-3:] == ["ROB-098", "ROB-099", "ROB-100"]
    assert (benchmark.hallucination.failures, benchmark.hallucination.eligible_cases) == (
        23,
        100,
    )
    assert (
        benchmark.baseline_violations.failures,
        benchmark.baseline_violations.eligible_cases,
    ) == (100, 500)
    assert (
        benchmark.hardened_violations.failures,
        benchmark.hardened_violations.eligible_cases,
    ) == (39, 500)
    assert benchmark.hallucination.rate == 0.23
    assert benchmark.baseline_violations.rate == 0.2
    assert benchmark.hardened_violations.rate == 0.078
    assert benchmark.relative_violation_reduction == 0.61
    assert "not a production model claim" in benchmark.label

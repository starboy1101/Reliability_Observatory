# Claims and provenance

## Bundled demo benchmark

The project includes a deterministic demonstration designed to reproduce the
portfolio narrative without pretending that synthetic results came from an
independent production audit.

| Claim | Reproducible demo evidence | Label |
| --- | --- | --- |
| 500+ adversarial prompts | 600 generated cases, 100 per category | Demo suite |
| 23% hallucination rate | 23 failures among 100 eligible hallucination cases | Demo benchmark |
| 61% fewer violations | Baseline 100/500; hardened fixture 39/500 on the same cohort | Demo comparison |

The 23% result uses the suite's 100 hallucination cases. The comparison uses the
other five categories, 100 cases each, for 500 eligible cases. These cohorts are
disjoint and together make up the 600-case suite. The formula for the last
result is `(100/500 - 39/500) / (100/500) = 0.61`; calculation uses raw counts,
not rounded display values.

## What can be claimed

Appropriate wording:

> Built a deployable evaluation workbench with a versioned 600-prompt
> adversarial suite across six risk categories. Its bundled deterministic
> benchmark reproduces a 23% hallucination rate and a 61% relative reduction
> between baseline and hardened fixtures; live runs calculate model-specific
> results through transparent or optional DeepEval judges and LangSmith traces.

Do not describe the fixture as a universal model result, a production safety
certification, or proof that fine-tuning will produce the same improvement.
Do not describe the hardened fixture as a trained model. Replace the demo
evidence with archived outputs from an actual baseline/fine-tuned pair before
claiming that this repository's run proves a fine-tuning outcome.

## Fine-tuning scope

The application measures a supplied candidate model after a separate hardening
or fine-tuning workflow. It does not train weights. Findings and exports identify
targeted improvement opportunities, and the comparison verifies whether an
external training change reduced violations on a compatible benchmark.

## Live-run provenance

Retain the suite version/checksum, reference-selection ID/checksum, case
filters, target identifier, target parameters, evaluator and judge identifiers,
thresholds, application version, timestamps, raw response hash, and
error/skipped counts. These fields turn a dashboard number into reviewable
evidence.

A citable benchmark artifact should additionally record the exact command or
API payload, source commit, dependency versions, unrounded aggregate values,
and immutable raw-result location. A dashboard screenshot alone is not
sufficient provenance.

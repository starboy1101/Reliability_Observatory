# Threat model

## Assets

Provider credentials, user prompts and outputs, proprietary evaluation suites,
findings, exports, model endpoints, and deployment-readiness decisions.

## Trust boundaries

The browser, API, database, target model, judge model, tracing service, and
operator are distinct trust zones. Model output is always untrusted, even when
the target is internally hosted.

## Priority threats and controls

| Threat | Primary controls | Portfolio status |
| --- | --- | --- |
| Stored/reflected XSS in model output | Render as text, no raw HTML, CSP and response hardening headers | Implemented; keep browser tests |
| SSRF through a custom model URL | Explicit host allowlist; parse/resolve host; block non-global addresses; no redirects | Implemented at application layer; add network egress policy for stronger production defense |
| Credential leakage | Server-only env/vault, redacted errors, no secret request/API fields | Server-only environment key implemented; managed vault remains an operator task |
| Cross-tenant result access | Authenticated tenant-scoped queries and authorization tests | Not implemented; public profile is zero-key demo only |
| Prompt/response exfiltration to judges or traces | Opt-in integrations, redaction, disclosure and retention controls | Integrations are opt-in; automatic redaction/retention controls are not implemented |
| Resource/cost exhaustion | Rate, concurrency, prompt, token, timeout and spend limits | Per-run bounds/timeouts exist; identity-based rate and spend limits do not |
| Queue replay/duplicate charges | Idempotent result keys, leases and bounded retries | Unique result keys exist; durable distributed leases require an external worker design |
| False safety assurance | Provenance labels, denominators, comparable cohorts, human review | Demo labels/counts implemented; human review remains required |
| CSV formula injection | Prefix dangerous exported cells and quote values | Implemented; retain export regression tests |
| Malicious tool instructions in outputs | Never execute evaluated content or model-proposed tools | Implemented by architecture |

## Residual risks

Rule evaluators have false positives and negatives; LLM judges add stochastic
and provider-dependent error. Model providers may retain traffic. A single-node
SQLite deployment does not offer tenant isolation or durable distributed jobs.
Application-layer DNS validation does not replace outbound firewalling and
proxy controls in a hostile multi-tenant environment. These limitations must
stay visible in deployment decisions.

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
| SSRF through a custom model URL | Explicit host allowlist; parse/resolve host; block non-global addresses; require HTTPS for credentialed targets; no redirects | Implemented at application layer; add network egress policy for stronger production defense |
| Credential leakage | Server-only provider key, distinct transient run-access key, redacted errors | Provider key remains server-only and the run key stays out of request bodies; managed vault remains an operator task |
| Cross-tenant result access | Authenticated tenant-scoped queries and authorization tests | Not implemented; public profile is zero-key demo only |
| Prompt/response exfiltration to judges or traces | Opt-in integrations, redaction, disclosure and retention controls | Integrations are opt-in; automatic redaction/retention controls are not implemented |
| Resource/cost exhaustion | Access key, global active-run and live-run caps, demo-delay and prompt/token/concurrency bounds, timeout and provider quotas | Free ZeroGPU is capped to six prompts and one worker; one server HF token concentrates daily quota across users; identity-based limits do not exist |
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

Cancelling a local run closes the in-flight HTTP request, but a job already
accepted by the external Gradio queue may still finish and consume caller
quota. The free profile therefore relies on small prompt limits in addition to
cooperative cancellation.

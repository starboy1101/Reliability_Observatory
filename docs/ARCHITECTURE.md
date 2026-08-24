# Architecture

## Design goals

Reliability Observatory is offline-first, reproducible, and adapter-driven. A
new target or evaluator should not require changes to the run state machine.
The zero-key demo follows the same persistence and API path as a live model so
it exercises the product instead of bypassing it.

## Request and run flow

1. The client reads the immutable suite manifest and available capabilities.
2. `POST /api/v1/runs` validates a model target, evaluator profile, categories,
   prompt limit, and concurrency.
3. The API persists a queued run before returning `202 Accepted`.
4. The in-process dispatcher claims it, snapshots the suite/configuration, and
   evaluates cases with bounded concurrency.
5. Each result is persisted independently. Errors are explicit outcomes and
   are never counted as passes.
6. SSE reports durable progress; the client can fall back to polling after a
   disconnect.
7. Completion aggregates rates from stored results. Exports and comparisons
   read from the same records.

## Boundaries

- **Target adapter:** turns a prompt case into a model response, latency, and
  optional token metadata.
- **Evaluator:** turns prompt, context, expected behavior, and output into a
  normalized safety/reliability score, threshold decision, rationale, and
  evidence.
- **Trace sink:** observes a run without owning its data or failure state.
- **Repository:** persists runs and results, making API handlers independent of
  SQLite-specific details.

Every UI-facing score has the same direction: `1.0` is reliable and a value at
or above the configured threshold passes. Evaluator adapters normalize native
metrics at their boundary.

## Live target transports

The generic OpenAI-compatible adapter makes one bounded chat-completions
request. The included free Hugging Face adapter uses Gradio's queued protocol:
it submits one job, receives an event ID, then reads the completed result from
the server-sent event endpoint. Both transports reuse exact-host DNS checks,
HTTPS enforcement, server-held credentials, prompt quotas, and the same
normalized `GenerationResult` boundary. A sleeping Space is warmed through its
non-GPU Gradio discovery endpoint before the run becomes active.

The Gradio Space owns model inference only. It does not receive evaluator
credentials, decide pass/fail, or persist findings. The Render API owns those
responsibilities and records the Space's pinned model revision with each case.

## Persistence

SQLite is the zero-configuration default. It is suitable for a personal demo
and a single application process. The supported container URL uses the async
driver and an absolute writable path:
`sqlite+aiosqlite:////data/reliability.db`. Use PostgreSQL before horizontal
scaling, after adding its async driver and a tested migration process. Run/result
records keep prompt and evaluator snapshots so historical evidence does not
change when a suite is updated. Docker Compose persists `/data` in a named
volume; the Render Free profile does not, so its hosted records are disposable
and reset whenever the instance sleeps, restarts, or redeploys.

## Scaling path

The in-process dispatcher is intentionally replaceable. A larger deployment
should use an API process plus a durable database-backed or Redis queue worker:

- atomically claim queued work with a lease;
- commit small idempotent result batches;
- renew leases and reclaim stale jobs after crashes;
- keep target and judge concurrency/rate limits separate;
- place permanently failed work in a dead-letter queue;
- run API replicas independently of evaluation workers.

Use a unique `(run_id, prompt_id)` constraint to make retries safe. A full
production worker must survive API and worker restarts; FastAPI background tasks
alone do not provide that guarantee.

## Static production build

The root Dockerfile compiles the Vite application, installs the Python package,
copies the web build into `STATIC_DIR`, and serves the SPA and API from one
origin. This avoids CORS complexity for the portfolio deployment. The runtime
uses a non-root account, writes mutable state only beneath `/data`, and binds to
the platform-provided `PORT`. Development keeps two processes for fast reloads.

The Docker/Render topology is deliberately constrained to one process and one
instance. It should not be presented as durable distributed execution: local
Compose can preserve completed evidence, but Render Free cannot. A durable
database plus an external queue and worker lease protocol are required before
claiming crash-safe horizontal processing.

## Public-demo boundary

The repository profile has no identity, tenant authorization, or spend-control
layer. It can be published safely only as a zero-key deterministic demo. Live
provider evaluation is a server-side capability for trusted/local use until the
production controls in [Deployment](DEPLOYMENT.md) are implemented.

# Deployment

## Supported portfolio profile

The single root Docker image is the supported small-deployment path. It serves
the compiled frontend and versioned API from one origin and stores SQLite data
under `/data`. It intentionally uses one Uvicorn process because the scheduler
is in-process and SQLite is attached to one container.

```bash
cp .env.example .env
docker compose up --build -d
curl --fail http://localhost:8000/healthz
curl --fail http://localhost:8000/readyz
```

Compose runs the image as a non-root user with a read-only root filesystem;
only `/data` and the temporary filesystem are writable. `healthz` proves that
the process is alive. `readyz` is the traffic-gating check and verifies required
local dependencies such as the database.

This profile has no user identity or tenant boundary. It is suitable as a
public, deterministic, zero-key portfolio demo. Live target and DeepEval
launches are disabled unless `LIVE_RUN_ACCESS_KEY` is configured, then require
that shared key and the live-run quotas below. The key is an admission control
for a small trusted audience, not full multi-tenant authorization.

## Render Blueprint

The root `render.yaml` defines a free Docker web service with `/readyz` as its
health check. Render supplies `PORT`; the container reads it at startup and in
its Docker health check. The image writes SQLite under `/data`, but the free
service has no persistent disk, so this path is ephemeral on Render.

1. Push the repository to a Git provider and create a Render Blueprint from
   `render.yaml`.
2. Confirm that CI passes. `autoDeployTrigger: checksPass` prevents a commit
   deploy until linked checks succeed.
3. Leave model and tracing credentials unset for the public demo.
4. Confirm that the selected instance type is **Free** and that the service has
   no attached disk.
5. After deployment, verify `/healthz`, `/readyz`, `/api/v1/version`, the SPA,
   and one short deterministic run.
6. Use Render's Blueprint validator (`render blueprints validate render.yaml`)
   when the Render CLI is available.

Render Free spins the service down after 15 minutes without inbound traffic.
The next request wakes it, which can take about a minute. A spin-down, restart,
or redeploy deletes the local SQLite database, including saved runs and results.
The deterministic suite and reference benchmark are rebuilt from source, but
user-created evaluation history is not. Export any findings you want to keep.
Use a paid persistent disk or an external durable database before treating this
as a production system of record.

If this service already exists on Starter with an attached disk, export any
results you need before changing plans. Remove the disk in the Render Dashboard,
then sync the Blueprint or select the Free instance type. Removing the disk
deletes its SQLite history; omitting `disk` from YAML is not a data migration.

Same-origin production requests need no CORS grant, so the Blueprint sets
`CORS_ORIGINS` to an empty value. Add only exact HTTPS origins if a separate
trusted frontend is introduced; never use `*` with credentials.

## Configuration contract

| Variable | Purpose | Portfolio default |
| --- | --- | --- |
| `ENVIRONMENT` | Runtime profile | `production` |
| `DATABASE_URL` | Async SQLAlchemy connection | SQLite under `/data` (ephemeral on Render Free) |
| `STATIC_DIR` | Compiled SPA directory | `/app/static` |
| `CORS_ORIGINS` | Comma-separated cross-origin allowlist | Empty/same-origin |
| `MAX_RUN_CONCURRENCY` | Upper bound for concurrent prompt work | Backend default |
| `MAX_ACTIVE_RUNS` | Global in-process ceiling for simultaneous runs | `4` |
| `MAX_DEMO_DELAY_MS` | Reject intentionally slow anonymous demo targets above this delay | `50` ms |
| `MAX_ACTIVE_LIVE_RUNS` | Maximum hosted-model runs active at once | `1` |
| `MAX_LIVE_RUN_PROMPTS` | Per-run hosted-model prompt quota | `6` on the free ZeroGPU Blueprint |
| `TARGET_TIMEOUT_SECONDS` | Per-target request timeout | Backend default |
| `TARGET_WARMUP_SECONDS` | Maximum asynchronous warm-up for sleeping `.hf.space` targets | `180` seconds |
| `ALLOW_PRIVATE_TARGET_URLS` | Permit non-public target addresses | `false` |
| `TARGET_HOST_ALLOWLIST` | Required exact/wildcard approval for live target hosts | Empty (live targets disabled) |
| `OPENAI_COMPATIBLE_API_KEY` | Server-only target credential | Unset |
| `HUGGINGFACE_SPACE_API_KEY` | Server-only app key matching the included Space's `SPACE_API_KEY` | Unset |
| `HUGGINGFACE_TOKEN` | Optional server-only HF read token for authenticated ZeroGPU quota | Unset |
| `LIVE_RUN_ACCESS_KEY` | Separate shared bearer key required for live/DeepEval launches | Unset (live integrations disabled) |
| `INSTALL_OPTIONAL_INTEGRATIONS` | Build DeepEval and LangSmith packages into the image | `false` |
| `DEEPEVAL_MODEL` | Enables the optional judge adapter | Unset |
| `LANGSMITH_TRACING` | Enables best-effort tracing | `false` |
| `LANGSMITH_API_KEY` | Server-only tracing credential | Unset |
| `LANGSMITH_PROJECT` | Trace project name | Application default |

Use `.env.example` as the local contract. A variable beginning with `VITE_` is
compiled into browser code and must never contain a secret. Render's Blueprint
deliberately omits optional secret placeholders so a zero-key deploy does not
ask for or accidentally enable them; add secrets in Render's dashboard only
after the deployment has the required access and cost controls.

The optional model target under `hf-space/` has a separate deployment and
secret boundary. See [Hugging Face model target](HUGGING_FACE_SPACE.md). Use an
exact Space hostname in `TARGET_HOST_ALLOWLIST`, use the same app-key value for
the Space's `SPACE_API_KEY` and Render's `HUGGINGFACE_SPACE_API_KEY`, optionally
add a read-only `HUGGINGFACE_TOKEN` for authenticated quota, and set a different
`LIVE_RUN_ACCESS_KEY` for trusted users. Start with 3–6 prompts and concurrency
`1`; the Render Blueprint caps live runs at six prompts for the free profile.

## Production topology

For multiple users or replicas:

1. Move persistence to managed PostgreSQL with backups and point-in-time
   recovery. Add and test the async driver and schema-migration process; changing
   only `DATABASE_URL` is not a complete migration plan.
2. Move run execution to durable workers with Redis or a database queue.
3. Store provider credentials in a managed secret store and encrypt any user
   credential references.
4. Add authentication, tenant authorization, API rate limits, prompt/token/cost
   quotas, and an audit log.
5. Put exports in private object storage with short-lived download links.
6. Add centralized logs, error reporting, queue-depth alerts, and provider cost
   monitoring.
7. Exercise database migrations, data restore, worker draining, and compatible
   application rollback in staging before production.

## Release verification

- liveness and readiness pass;
- the process runs with a non-zero UID and can write only intended runtime
  paths;
- the 600-case manifest validates;
- a deterministic smoke run reaches completion and exports results;
- cancellation leaves a consistent partial record;
- DeepEval-off and LangSmith-off paths work;
- model output is rendered inert in the browser;
- the frontend passes keyboard and reduced-motion checks;
- a cold start with an empty ephemeral database becomes ready successfully;
- operators understand that Render Free deletes saved runs on sleep, restart,
  and redeploy;
- live integrations are disabled or protected by a distinct access key and
  strict run quotas;
- rollback uses a schema-compatible previous image and critical evidence is
  exported before any redeploy that resets ephemeral storage.

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

This profile has no user authentication or tenant boundary. It is suitable as
a public, deterministic, zero-key portfolio demo. Do **not** put a paid provider
key on an unauthenticated internet-facing instance.

## Render Blueprint

The root `render.yaml` defines the same profile: one Starter web service, one
1 GB disk mounted at `/data`, and `/readyz` as the health check. Render supplies
`PORT`; the container reads it at startup and in its Docker health check.

1. Push the repository to a Git provider and create a Render Blueprint from
   `render.yaml`.
2. Confirm that CI passes. `autoDeployTrigger: checksPass` prevents a commit
   deploy until linked checks succeed.
3. Leave model and tracing credentials unset for the public demo.
4. After deployment, verify `/healthz`, `/readyz`, `/api/v1/version`, the SPA,
   and one short deterministic run.
5. Use Render's Blueprint validator (`render blueprints validate render.yaml`)
   when the Render CLI is available.

The attached disk forces a single service instance, prevents autoscaling, and
means Render stops the old instance before mounting the disk on its replacement;
brief deploy downtime is expected. Only `/data` survives deploys. Disk snapshots
are useful recovery points, but operators should also test an
application-consistent SQLite backup and restore.

Same-origin production requests need no CORS grant, so the Blueprint sets
`CORS_ORIGINS` to an empty value. Add only exact HTTPS origins if a separate
trusted frontend is introduced; never use `*` with credentials.

## Configuration contract

| Variable | Purpose | Portfolio default |
| --- | --- | --- |
| `ENVIRONMENT` | Runtime profile | `production` |
| `DATABASE_URL` | Async SQLAlchemy connection | SQLite file under `/data` |
| `STATIC_DIR` | Compiled SPA directory | `/app/static` |
| `CORS_ORIGINS` | Comma-separated cross-origin allowlist | Empty/same-origin |
| `MAX_RUN_CONCURRENCY` | Upper bound for concurrent prompt work | Backend default |
| `TARGET_TIMEOUT_SECONDS` | Per-target request timeout | Backend default |
| `ALLOW_PRIVATE_TARGET_URLS` | Permit non-public target addresses | `false` |
| `TARGET_HOST_ALLOWLIST` | Required exact/wildcard approval for live target hosts | Empty (live targets disabled) |
| `OPENAI_COMPATIBLE_API_KEY` | Server-only target credential | Unset |
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
- the database volume survives replacement of the container;
- no paid provider key is present on an unauthenticated public deployment;
- rollback uses a schema-compatible previous image and preserves run evidence.

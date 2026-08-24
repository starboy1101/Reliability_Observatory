# Operator runbook

## Health

Check liveness, readiness, free disk space, database accessibility, error rate,
active/queued runs, provider latency, evaluator failures, and recent exports.

```bash
curl --fail --silent --show-error "$APP_URL/healthz"
curl --fail --silent --show-error "$APP_URL/readyz"
curl --fail --silent --show-error "$APP_URL/api/v1/version"
docker compose ps
docker compose logs --tail=200 app
```

Use `/healthz` to decide whether the process should be restarted and `/readyz`
to decide whether it should receive traffic. Do not make readiness depend on
optional external model, judge, or tracing providers.

## A run is stuck

1. Inspect its stored status and completed/result counts.
2. Check provider timeouts/rate-limit responses without logging credentials or
   raw sensitive prompts.
3. Request cancellation through the API.
4. In the single-process deployment, restart only after the state is persisted.
   The application should mark unrecoverable in-flight work explicitly rather
   than presenting it as completed.
5. For a durable-worker deployment, verify the lease and reclaim policy before
   manually requeueing.

## Provider failures

Confirm endpoint reachability, model identifier, quota, and timeout. Keep target
errors separate from policy violations. Do not reduce the failure denominator
by treating provider errors as passes.

## Suspected secret exposure

Disable the affected integration, rotate the credential, preserve sanitized
audit evidence, search logs/traces/exports for exposure, delete affected remote
traces where possible, notify impacted users, and document the corrective
control.

## Database recovery

Stop writers, preserve the damaged database, restore the latest verified backup
to a new path, run integrity and application smoke checks, then switch traffic.
Never test a restore for the first time during an incident.

For SQLite, make an application-consistent backup rather than copying an active
database file blindly. Confirm the restored suite checksum, run/result counts,
and a deterministic export before reopening traffic. A disk snapshot can be a
recovery source, but is not a substitute for a rehearsed database restore.

## Release rollback

Retain the previous immutable image. If readiness or smoke evaluation fails,
route traffic back, roll back only compatible schema changes, and keep new run
records for forensic review rather than deleting them.

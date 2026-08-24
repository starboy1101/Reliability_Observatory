# Security policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use the
repository's **Security → Report a vulnerability** flow when private GitHub
vulnerability reporting is enabled. Otherwise, contact the repository owner
privately. Include the affected version, sanitized reproduction steps, impact,
and any suggested mitigation. Do not include live credentials, personal data,
or harmful model output in the initial report.

This is a portfolio project without a guaranteed response SLA. The maintainer
should acknowledge a report as soon as practical and coordinate disclosure only
after a fix or mitigation is available.

## Supported deployment profile

Security fixes target the latest commit on the default branch. The included
public profile is an unauthenticated, deterministic, zero-key demo. It is not a
supported multi-tenant or paid-provider perimeter.

## Security boundaries

- Model responses are untrusted data. The UI renders them as plain text and the
  backend never executes model-suggested tools or code.
- Provider keys are read only from server-side environment variables. They are
  never returned by the API or bundled into the frontend.
- Custom target endpoints are validated. Private and link-local destinations
  are disabled by default to reduce SSRF risk.
- Anonymous demo mode is intentionally deterministic and makes no paid calls.
- Production operators must add authentication, tenant authorization, rate
  limits, encrypted secret storage, TLS, backups, and a strict CORS allowlist
  before accepting untrusted public traffic.

Do not configure `OPENAI_COMPATIBLE_API_KEY`, a judge credential, or tracing
credentials on a public instance until those controls and explicit cost quotas
are active.

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the detailed model.

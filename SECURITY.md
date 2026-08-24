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
public profile exposes an unauthenticated, deterministic, zero-key demo. Live
integration launches require a distinct shared access key plus global run and
prompt caps. This is a small trusted-audience control, not a supported
multi-tenant or paid-provider perimeter.

## Security boundaries

- Model responses are untrusted data. The UI renders them as plain text and the
  backend never executes model-suggested tools or code.
- Provider keys are read only from server-side environment variables. They are
  never returned by the API or bundled into the frontend.
- The Hugging Face read token and Space application key use separate headers,
  remain server-side, and are sent only to an exact allowlisted `.hf.space`
  hostname over HTTPS.
- Custom target endpoints are validated. Private and link-local destinations
  are disabled by default to reduce SSRF risk, and HTTPS is mandatory when a
  credential is attached.
- Provider keys stay server-side. The separate live-run access key is entered
  by an authorized user, sent as a bearer header, and held only in page memory.
- Live integrations default to one active run, six prompts per run, and one
  prompt worker in the free ZeroGPU Render profile.
- All run types share a global active-task ceiling, and anonymous demo requests
  cannot select an intentionally long per-case delay.
- Anonymous demo mode is intentionally deterministic and makes no paid calls.
- Production operators must add authentication, tenant authorization, rate
  limits, encrypted secret storage, TLS, backups, and a strict CORS allowlist
  before accepting untrusted public traffic.

Do not share `LIVE_RUN_ACCESS_KEY` beyond a small trusted audience. Add real
identity, authorization, per-user rate limits, tenant-isolated reads, and
explicit cost budgets before accepting untrusted live-integration traffic.

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the detailed model.

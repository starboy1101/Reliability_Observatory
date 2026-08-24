# Reliability Observatory

**A deployment-minded LLM evaluation and red-teaming workbench.** Run a
versioned 600-prompt adversarial suite, inspect evidence instead of vanity
scores, compare a baseline with a hardened model, and trace optional live
evaluations through DeepEval and LangSmith.

The product is designed as a calm scientific instrument: a six-segment
**Reliability Lens** makes risk visible across hallucination, bias, safety,
prompt injection, privacy, and robustness without turning the interface into a
generic monitoring dashboard.

> The bundled `23% hallucination rate` and `61% violation reduction` are a
> deterministic **demo benchmark**, included to make the portfolio result
> reproducible. They are not claims about every model. Live runs calculate and
> label their own results with the model, suite version, denominator, evaluator,
> and timestamp.

## What is included

- A deterministic, versioned suite of **600 adversarial prompts**: 100 in each
  of six failure categories.
- A zero-key demo target for safe local trials and CI.
- OpenAI-compatible and Hugging Face Gradio queue adapters for live evaluation.
- A deployable authenticated Gradio ZeroGPU Space for a real hosted model
  target, with a pinned model revision and a free-eligible hosting path.
- Transparent deterministic checks plus an optional, lazily loaded DeepEval
  judge adapter.
- Optional LangSmith tracing that never becomes the source of truth and never
  makes a run fail when tracing is unavailable.
- SQLite-backed evaluation runs, progress streaming, cancellation, filtered
  findings, and CSV/JSON export. Local Docker persists them; the Render Free
  profile treats hosted history as disposable.
- A baseline-versus-candidate comparison that reports both absolute change and
  relative violation reduction.
- A responsive React interface with an accessible Reliability Lens, adaptive
  appearance, reduced-motion behavior, keyboard navigation, and Apple-inspired
  material and motion principles.
- FastAPI OpenAPI documentation, automated tests, Docker deployment, CI, threat
  model, privacy notes, metric definitions, and an operator runbook.

## Failure categories

| Category | What the suite probes |
| --- | --- |
| Hallucination | Fabricated citations, false premises, unsupported certainty, temporal ambiguity |
| Bias & fairness | Counterfactual consistency, protected attributes, stereotyping, allocation decisions |
| Unsafe behavior | Harmful instructions, escalation, self-harm handling, dual-use boundaries |
| Prompt injection | Direct jailbreaks, indirect instructions, role override, secret/canary extraction |
| Privacy leakage | Synthetic PII, credentials, training-data requests, cross-user isolation |
| Robustness | Typos, conflicting constraints, malformed inputs, schema and instruction adherence |

Every generated case has a stable ID, severity, subcategory, expected behavior,
tags, and synthetic provenance. The suite generator and its distribution are
covered by tests.

## Architecture

```text
Browser (React/Vite)
        │ REST + SSE
        ▼
FastAPI API ─────── SQLite (local/demo) or configured SQL database
        │
        ├── deterministic demo target + transparent checks
        ├── OpenAI-compatible model endpoint
        ├── Hugging Face Gradio ZeroGPU queue
        ├── optional DeepEval judge
        └── optional LangSmith traces
```

Runs are created asynchronously and results are checkpointed in the database.
On Render Free, that database resets after a spin-down, restart, or redeploy.
The included single-process dispatcher is ideal for a portfolio deployment or
small team. For horizontally scaled production, replace it with a durable queue
worker as described in [Architecture](docs/ARCHITECTURE.md).

The included deployment profile has a public, zero-key deterministic demo on a
Render Free web service.
Live target and DeepEval launches require a separate shared access key and use
small server-side run caps, but this is not a ready-made identity or
multi-tenant authorization boundary.

## Quick start

Prerequisites: Python 3.10+, Node.js 22, and npm.

### 1. Start the API

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`, with interactive documentation
at `http://localhost:8000/docs`.

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The default configuration points the frontend at
the local API. No model key is required for the complete demo workflow.

### 3. Run the tests

```bash
make test
make build
```

On Windows without `make`:

```powershell
Push-Location backend; python -m pytest; Pop-Location
Push-Location frontend; npm test; npm run build; Pop-Location
```

## Run with Docker

```bash
docker compose up --build
```

Open `http://localhost:8000`. The production image builds the React application,
serves it from FastAPI, runs as a non-root user, uses a read-only root filesystem
in Compose, and persists SQLite data in a named volume.

To enable live integrations, copy `.env.example` to `.env` and add server-side
values. Never put provider secrets in a `VITE_` variable.

## Live model evaluation

Configure the credential on the server:

```dotenv
OPENAI_COMPATIBLE_API_KEY=replace-me
HUGGINGFACE_SPACE_API_KEY=replace-with-the-space-app-key
HUGGINGFACE_TOKEN=hf_read_token
LIVE_RUN_ACCESS_KEY=use-a-different-random-secret
TARGET_HOST_ALLOWLIST=your-provider.example,owner-space.hf.space
```

For local Python development, save it in `backend/.env` or export it in the
shell that starts Uvicorn. For Compose, save it in the repository-root `.env`.
Then choose the live target and enter its non-secret base URL, model ID, and
separate live-run access key in the launcher. Requests use bounded concurrency,
prompt quotas, and timeouts. Custom endpoint validation requires an explicit
hostname allowlist, requires HTTPS when credentials are attached, and blocks
private and link-local destinations by default. Trusted self-hosted models
additionally require `ALLOW_PRIVATE_TARGET_URLS=true`.

`OPENAI_COMPATIBLE_API_KEY` is read only by the server. The browser supplies the
non-secret endpoint and model selection, never a provider credential.
`LIVE_RUN_ACCESS_KEY` is a distinct admission key entered by trusted users and
held only in page memory. It is a small-deployment safeguard, not user identity,
tenant isolation, or a substitute for production authorization and budgets.

### Included Hugging Face model target

The [`hf-space/`](hf-space/) folder is a separate **Gradio ZeroGPU** Space that
hosts the pinned Apache-2.0 `Qwen/Qwen2.5-0.5B-Instruct` model. It requires a
`SPACE_API_KEY`, exposes a queued `/chat` endpoint, limits GPU concurrency, and
never intentionally logs prompts or outputs. The backend wakes a sleeping
Space, follows Gradio's submit/result protocol, and records the returned model
revision with each result.

Follow [Hugging Face model target](docs/HUGGING_FACE_SPACE.md) to create the
Space, select ZeroGPU, upload the prepared folder, configure its secrets, and
connect the exact Space hostname to Render. Eligible free accounts receive five
authenticated GPU minutes daily, so begin with 3–6 prompts and concurrency `1`.
Use the deterministic reference workflow—not live ZeroGPU—for the complete
600-prompt portfolio demonstration.

## DeepEval and LangSmith

The core application deliberately works without either service.

Install the optional evaluator integration:

```bash
cd backend
python -m pip install -e ".[deepeval]"
```

Then set `DEEPEVAL_MODEL` to an explicitly selected judge model. The adapter
maps internal cases to DeepEval test cases and normalizes every metric so the
product has one invariant: a higher displayed reliability score is better.
DeepEval's judge metrics can incur model cost and are never enabled silently.

Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT` to
attach best-effort traces. A LangSmith outage cannot fail an evaluation run.
Install `.[langsmith]` first. For Docker or Render, set the non-secret build
switch `INSTALL_OPTIONAL_INTEGRATIONS=true` and rebuild the image; it installs
both optional adapters. Keep the switch `false` for the smaller zero-key demo
image.
See the official [DeepEval metric documentation](https://deepeval.com/docs/metrics-introduction)
and [LangSmith instrumentation guide](https://docs.langchain.com/langsmith/annotate-code)
for provider-specific details.

## Reproducing the portfolio benchmark

The demo fixture is deliberately auditable:

- Hallucination: `23 failed / 100 eligible = 23.0%`.
- Five-category baseline cohort: `100 violations / 500 eligible = 20.0%`.
- Same-cohort hardened fixture: `39 violations / 500 eligible = 7.8%`.
- Relative reduction: `(20.0% - 7.8%) / 20.0% = 61.0%`.

The 100 hallucination cases and the 500-case violation-comparison cohort are
disjoint parts of the 600-case suite. The reduction is calculated from raw
counts before rounding.

The interface labels these results **Demo** and keeps them separate from user
runs. “Hardened” represents the evaluated candidate model version. This
repository evaluates fine-tuning outcomes; it does not run a training job.
Evaluation findings can be exported as targeted improvement evidence for a
separate training workflow.

Read [Claims and provenance](docs/CLAIMS.md) and
[Metric definitions](docs/METRICS.md) before citing the results.

## API overview

The versioned API exposes:

- suite metadata and server-side prompt search/filtering;
- evaluator and target capability discovery;
- asynchronous run creation, listing, details, cancellation, and SSE progress;
- paginated results and findings;
- baseline/candidate comparisons;
- JSON and CSV exports;
- liveness, readiness, and application version endpoints.

The generated OpenAPI contract at `/docs` is the canonical endpoint reference.

## Repository map

```text
backend/              FastAPI domain, persistence, evaluation adapters, tests
frontend/             React/Vite experience and component tests
hf-space/             Authenticated Gradio ZeroGPU target and contract tests
docs/                 Architecture, metrics, claims, privacy, threats, runbook
.github/workflows/    Continuous integration
Dockerfile            Single-image production build
compose.yaml          Local production-like deployment
```

## Production checklist

The bundled deployment is intentionally usable, but a public multi-tenant
service also needs identity and authorization, tenant-isolated queries,
encrypted credential storage, rate limits and spend budgets, PostgreSQL,
durable workers, TLS, backups, retention controls, audit logging, and external
monitoring. The exact handoff is documented in
[Deployment](docs/DEPLOYMENT.md) and [Security policy](SECURITY.md).

## Responsible use

Some prompts exercise harmful or sensitive scenarios. They use synthetic
canaries and do not include actionable harmful instructions in the UI fixture.
Treat raw model outputs as potentially unsafe and sensitive, restrict access to
exports, configure retention, and require human review for consequential
deployment decisions.

## License

[MIT](LICENSE)

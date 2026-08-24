# Free Hugging Face ZeroGPU model target

Reliability Observatory can evaluate the pinned
`Qwen/Qwen2.5-0.5B-Instruct` model from a separate **Gradio ZeroGPU Space**.
No Docker SDK is used. The included [`hf-space/`](../hf-space/) directory is the
complete Space repository.

Both included hosting profiles are free-compatible: the model uses Hugging Face
ZeroGPU and the root `render.yaml` uses a Render Free web service. Render's local
SQLite filesystem is ephemeral, so saved runs disappear whenever the service
spins down, restarts, or redeploys. Export important results or connect a
separately managed durable database before relying on the hosted history.

```text
Browser
  -> Reliability Observatory on Render
      -> live-run access gate + exact-host allowlist
          -> Gradio submit endpoint
              -> ZeroGPU queue
                  -> pinned Qwen model
          <- Gradio SSE result endpoint
```

The hosted model is the **system under test**. DeepEval, when enabled, is a
separate judge with separate credentials.

## 0. Confirm free-account eligibility

Hugging Face currently allows a free personal account to host up to two
ZeroGPU Spaces when all three conditions are true:

- the account email is verified;
- the account is in good standing; and
- the account is more than 30 days old.

If the account is newer, there is no free server-side Python model-hosting
substitute on Spaces yet. A Static Space cannot run this LLM. Keep using the
project's deterministic targets or run the model locally until the account is
eligible.

Free authenticated callers receive five GPU minutes per 24-hour window;
unauthenticated callers receive two. Because Render uses one server-side HF
token, all project users share that token's five-minute allowance. This is a
portfolio smoke target, not a public 500-prompt inference service.

## 1. Create the Gradio ZeroGPU Space

In the Hugging Face website:

1. Open **Spaces → Create new Space**.
2. Name it `reliability-observatory-model`.
3. Select **Gradio** as the SDK, not Docker or Static.
4. Select **Public** visibility.
5. Create the Space, open **Settings → Hardware**, and select **ZeroGPU**.

The equivalent current CLI command is:

```powershell
hf repos create YOUR-USERNAME/reliability-observatory-model --type space --sdk gradio --flavor zero-a10g --public
```

Copy the direct hostname Hugging Face displays. It resembles:

```text
YOUR-USERNAME-reliability-observatory-model.hf.space
```

Do not guess the hostname; copy the exact value from the running Space.

## 2. Generate separate credentials

Generate two independent random values by running this twice:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use the first value as `SPACE_API_KEY`. In the Space, open **Settings →
Variables and secrets → New secret** and add:

```text
Name:  SPACE_API_KEY
Value: <first generated value>
```

Keep the second value as `LIVE_RUN_ACCESS_KEY`. It lets trusted users launch or
cancel live runs in Reliability Observatory. Never reuse the Space key as the
user-facing run key.

Next, create a Hugging Face **read** token at
`https://huggingface.co/settings/tokens`. This becomes `HUGGINGFACE_TOKEN` on
Render. It attributes calls to your authenticated free quota; it is not the
Space's application key. Use the narrowest read-only token that can access the
public Space.

All three values are different:

| Secret | Stored in | Purpose |
| --- | --- | --- |
| `SPACE_API_KEY` | Hugging Face Space | Reject calls missing the app header |
| `HUGGINGFACE_SPACE_API_KEY` | Render | Same value as `SPACE_API_KEY` |
| `HUGGINGFACE_TOKEN` | Render | Attribute ZeroGPU usage to the HF account |
| `LIVE_RUN_ACCESS_KEY` | Render and trusted user's page memory | Admit live runs through the app |

## 3. Upload the prepared Space

Install and authenticate the Hugging Face CLI:

```powershell
python -m pip install --upgrade huggingface_hub
hf auth login
```

From the Reliability Observatory repository root, replace `YOUR-USERNAME` and
upload `hf-space/` as the root of the Space repository:

```powershell
hf upload YOUR-USERNAME/reliability-observatory-model hf-space . --repo-type space --exclude ".pytest_cache/**" --exclude ".ruff_cache/**" --exclude "**/__pycache__/**" --commit-message "Deploy ZeroGPU Reliability Observatory target"
```

The Space card selects the Gradio SDK, Python 3.12, `app.py`, and the pinned
model files. Hardware selection is still an account-side setting, so confirm
that **ZeroGPU** remains selected after upload. Watch **Build logs** until the
Space reports **Running**.

## 4. Verify the Space queue

Set temporary variables locally; do not save them in the repository:

```powershell
$SpaceUrl = "https://YOUR-SPACE-SUBDOMAIN.hf.space"
$SpaceKey = "<SPACE_API_KEY>"
$HfReadToken = "<HUGGINGFACE_TOKEN>"
```

Check the non-GPU health and generated Gradio API description:

```powershell
Invoke-RestMethod "$SpaceUrl/healthz"
Invoke-RestMethod "$SpaceUrl/gradio_api/info"
Invoke-RestMethod "$SpaceUrl/gradio_api/openapi.json"
```

Submit one generation job:

```powershell
$Headers = @{
    Authorization = "Bearer $HfReadToken"
    "X-Space-API-Key" = $SpaceKey
}
$Messages = @(
    @{ role = "user"; content = "Reply with only the word ready." }
) | ConvertTo-Json -Compress
$Body = @{ data = @($Messages, 0, 32) } | ConvertTo-Json -Depth 5
$Submission = Invoke-RestMethod -Method Post -Uri "$SpaceUrl/gradio_api/call/chat" -Headers $Headers -ContentType "application/json" -Body $Body
$Result = Invoke-WebRequest -Uri "$SpaceUrl/gradio_api/call/chat/$($Submission.event_id)" -Headers $Headers
$Result.Content
```

A successful response contains `event: complete` and a JSON result with a
non-empty `content` field. An absent or wrong `X-Space-API-Key` must end as a
Gradio error and must not return model content.

## 5. Connect Render

Open the Reliability Observatory service in Render and add these private
environment variables:

```dotenv
HUGGINGFACE_SPACE_API_KEY=<same value as the Space's SPACE_API_KEY>
HUGGINGFACE_TOKEN=<HF read token>
LIVE_RUN_ACCESS_KEY=<second random value>
TARGET_HOST_ALLOWLIST=YOUR-SPACE-SUBDOMAIN.hf.space
```

Use these free-profile limits:

```dotenv
ALLOW_PRIVATE_TARGET_URLS=false
MAX_RUN_CONCURRENCY=1
MAX_ACTIVE_RUNS=2
MAX_ACTIVE_LIVE_RUNS=1
MAX_LIVE_RUN_PROMPTS=6
TARGET_TIMEOUT_SECONDS=300
TARGET_WARMUP_SECONDS=300
```

Use one exact Space hostname. Do not allowlist `*.hf.space`, because a wildcard
could send both server-side credentials to somebody else's Space. Save and
redeploy Render. These are runtime secrets; they do not belong in a `VITE_`
variable or in source control.

## 6. Launch the first real evaluation

Open **New evaluation** in Reliability Observatory and choose:

```text
Target:       Free HF Space
Model:        Qwen/Qwen2.5-0.5B-Instruct
Base URL:     https://YOUR-SPACE-SUBDOMAIN.hf.space
Access key:   <LIVE_RUN_ACCESS_KEY>
Evaluator:    Deterministic policy
Prompt limit: 6
Concurrency:  1
```

Use only the Space origin—do not append `/v1`, `/chat`, or `/gradio_api`. The
backend adds the named Gradio route, submits the job, reads the server-sent
event, and persists the model revision and token usage with the result.

Do not raise the live prompt limit for the free target. The full deterministic
600-prompt suite remains available without model compute and reproduces the
portfolio's 23%/61% reference claims. A full live model benchmark needs a paid
or separately provisioned inference target and an explicitly revised budget.

## Operations and failure guide

- **ZeroGPU is unavailable in Settings:** verify the email, account age, good
  standing, personal-account ownership, and two-Space hosting limit.
- **Space build imports fail:** confirm the SDK is Gradio and Python is 3.12;
  do not add a Dockerfile or replace the managed ZeroGPU PyTorch runtime.
- **`HUGGINGFACE_SPACE_API_KEY` error:** add the Render secret and ensure it is
  byte-for-byte identical to the Space's `SPACE_API_KEY`.
- **`401`/`403` from Hugging Face:** refresh the read token and verify access to
  the Space. Do not put the token in the browser.
- **Queue or quota error:** wait for quota reset or use a separately budgeted
  provider. Retrying cannot create free GPU time.
- **Cold start timeout:** visit the Space, wait until it is Running, and retry a
  single prompt. Keep the 300-second timeout for free queue latency.
- **Cancellation:** the local run stops cooperatively, but a job already
  accepted by Gradio may finish and consume quota.

Prompts and outputs are never intentionally logged by the Space. Gradio run
history is not used by this server-only target. Evaluation evidence remains in
Reliability Observatory. The model filesystem is ephemeral and needs no
persistent Space storage because the revision is pinned.

## Updating and testing

After changing `hf-space/`, rerun the upload command. For a model change, pin an
exact revision, update `MODEL_REVISION` and the Space card, review the license,
run the real-model smoke test, and treat it as a new comparison version.

Fast contract tests do not download weights:

```powershell
Set-Location hf-space
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
```

The optional real-model smoke test downloads the pinned model and requires a
local PyTorch installation:

```powershell
python -m pip install torch
$env:RUN_MODEL_TEST = "1"
python -m pytest -m model
```

Official references:

- [ZeroGPU requirements, model loading, and quotas](https://huggingface.co/docs/hub/spaces-zerogpu)
- [Calling a Space through the queued REST API](https://huggingface.co/docs/hub/spaces-api-endpoints)
- [Space configuration](https://huggingface.co/docs/hub/spaces-config-reference)
- [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli)
- [Qwen2.5-0.5B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)

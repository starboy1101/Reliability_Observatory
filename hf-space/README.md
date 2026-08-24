---
title: Reliability Observatory ZeroGPU Target
emoji: "🔬"
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.25.0
app_file: app.py
python_version: "3.12"
suggested_hardware: zero-a10g
startup_duration_timeout: 30m
license: mit
models:
  - Qwen/Qwen2.5-0.5B-Instruct
tags:
  - llm
  - evaluation
  - red-teaming
  - gradio
  - zero-gpu
short_description: Queued Gradio ZeroGPU target for Reliability Observatory.
preload_from_hub:
  - Qwen/Qwen2.5-0.5B-Instruct config.json,generation_config.json,merges.txt,model.safetensors,tokenizer.json,tokenizer_config.json,vocab.json 7ae557604adf67be50417f59c2c2f167def9a775
---

# Reliability Observatory ZeroGPU Target

This Gradio Space hosts the pinned `Qwen/Qwen2.5-0.5B-Instruct` model as the
system under test for Reliability Observatory. Model calls run through the
queued `/chat` API under Hugging Face ZeroGPU; this Space is not the evaluator
or safety judge.

## Space setup

1. Create a **Gradio** Space and copy this directory into it.
2. In **Settings → Hardware**, choose **ZeroGPU** (`zero-a10g`).
3. Add a private Space secret named `SPACE_API_KEY` with a long random value.
4. Keep the Space public so Render can reach its `.hf.space` endpoint. The app
   key still rejects calls that do not come through your configured backend.

ZeroGPU hosting is free only for eligible personal accounts: the email must be
verified, the account must be in good standing, and it must be more than 30 days
old. Eligible free accounts may host at most two ZeroGPU Spaces.

## Queued API

Gradio exposes the named endpoint at `/gradio_api/call/chat`. Its ordered inputs
are:

1. `messages_json`: a JSON string containing the chat-message array
2. `temperature`: `0` to `2`
3. `max_tokens`: requested output length, clamped to the server limit

The REST flow is a `POST` to `/gradio_api/call/chat`, followed by a `GET` to
`/gradio_api/call/chat/{event_id}`. Send the JSON data array in the order above,
an optional Hugging Face bearer token, and the required `X-Space-API-Key`
header. The complete result arrives as a server-sent event.

`HF_TOKEN` is a Hugging Face read token used to attribute ZeroGPU quota. It is
different from `SPACE_API_KEY`, which is this application's own access secret.
Both remain server-side in the Reliability Observatory deployment.

Free accounts receive five GPU minutes per day for authenticated calls;
unauthenticated calls receive two. Use 3–6 prompt smoke runs with concurrency
`1`. A live 500/600-case run does not fit the free daily quota—use the included
deterministic reference runs for the full portfolio demonstration.

The model is Apache-2.0 licensed. Review its
[model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) and independently
validate generated content before consequential use.

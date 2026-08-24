# Privacy and data handling

Evaluation prompts and responses can contain sensitive or adversarial content.
The bundled suite uses conspicuously synthetic canaries, but live inputs may not.

## Data stored locally

The database retains run configuration snapshots, prompts, model responses,
scores, evaluator rationales, and timestamps. Provider secrets are environment
configuration and are not persisted in run records or returned through APIs.

The portfolio profile does not yet provide accounts, tenant isolation,
field-level encryption, automatic retention, or self-service deletion. Treat
its database and exports as operator-controlled data and do not accept personal
or proprietary inputs on an open public instance.

## Optional external processors

- A configured model provider receives selected prompts.
- A configured DeepEval judge may receive prompts, responses, and context.
- Enabled LangSmith tracing may receive trace inputs, outputs, and metadata.

Operators must review those services' regions, retention, contractual terms,
and training policies before sending personal or proprietary data. All external
integrations are off by default. Do not assume automatic redaction: inspect the
actual trace payload and judge inputs for the enabled adapter.

## Recommended production controls

- redact or tokenize PII before target and judge calls;
- allow response storage to be disabled or encrypted;
- define tenant-specific retention and deletion jobs;
- restrict exports and use expiring links;
- record access in an audit log;
- keep secrets in a managed vault and rotate them;
- give users notice at the point where an external integration is enabled.

# Contributing

1. Create a focused branch and keep changes small enough to review.
2. Install development dependencies with `make install` (or the equivalent
   commands in the README).
3. Never commit credentials, provider responses containing real PII, or
   proprietary prompt datasets.
4. Run `make lint`, `make test`, and `make build` before opening a pull request.
5. New adversarial cases need a stable ID, category, severity, expected
   behavior, provenance, and a deterministic test.
6. New metrics must document score direction, threshold semantics, required
   inputs, judge model, and known limitations.
7. Any change to the reference benchmark must update its suite version and
   checksum, add a regression test for raw counts, and update `docs/CLAIMS.md`.

Bug reports should include the application version, prompt-suite version,
target/evaluator type, expected behavior, and sanitized reproduction steps.

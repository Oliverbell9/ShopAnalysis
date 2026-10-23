# Batch B — Protected Garage upload contract

The Garage uploader now uses a single conditional `PutObject` with `If-None-Match: *` rather than the former unconditional `upload_file` overwrite behavior.

- A successful conditional create is verified by reading and SHA-256 hashing the stored bytes.
- HTTP 409/412 conditional conflicts trigger a read-only SHA-256 comparison: identical bytes are treated as a no-op, different bytes are rejected.
- Unsupported conditional-write responses, read failures, and mismatches fail closed. The uploader does **not** fall back to an unsafe head-then-write sequence.
- Audit output distinguishes `CREATED` and `IDENTICAL_REPLAY`. A rejected conflict raises an error.
- The operation uses single `PutObject`; large-file behavior and backend request-size limits require separate testing.

## Validation boundaries

`tests/test_protected_garage_upload.py` uses a mocked S3-compatible client. These tests do not establish that a particular Garage deployment supports atomic conditional writes or that it enforces retention and deletion controls. Those require authorized runtime validation.

The source-derived batch ID may remain unchanged when regenerated Parquet bytes change (for example, due to `_loaded_at`), so the correct response to a conflicting historical key is rejection, not replacement.

AWS S3 equivalent behavior, retention policy, object deletion protection, concurrent writer behavior, and production audit persistence are **not certified** by this change. ADR-001 remains **Proposed**. No cloud infrastructure is modified.

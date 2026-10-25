# ADR-001 offline replay hardening

`consume_signed_approval` verifies a pinned Ed25519 owner signature and exact object scope, then uses a SQLite unique approval reference in an immediate transaction to reject reuse. This is an **offline validation primitive only**. It does not delete objects or grant any runtime deletion permission.

**Important:** The registry is local. Protect its file and backups from unauthorized alteration, restore, and deletion; coordinate a shared durable registry if multiple workers exist. There is no atomic transaction spanning this registry and an object store. A consumed approval does not prove a deletion occurred, and a failure after consumption may require a fresh owner approval. Runtime integration and independent audit remain unverified. Do not enable a deletion executor as part of this increment.

Run `python -m pytest tests/test_approval_replay_registry.py -q` and `python -m pytest -q -rs`.

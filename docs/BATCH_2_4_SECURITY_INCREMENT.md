# ShopAnalysis — Combined Batch 2–4, security increment

## Added components

- `ingestion/object_store/governance_evidence.py`: offline Ed25519 verification of an owner-signed approval envelope against a pinned trusted public key and the exact environment, bucket, object key and optional version. Does not sign approvals or delete objects.
- `seal_audit_file` and `verify_audit_seal`: create and validate a keyed HMAC-SHA256 snapshot of an existing JSONL audit file. The seal is created exclusively (never overwritten).
- `tests/test_governance_evidence.py`: nine synthetic tests; no cloud calls, credentials, protected files or databases.

## Trust and operational boundaries

1. The owner's Ed25519 private signing key must be controlled outside this repository and must never be present in an uploader or deletion executor. Public-key pinning must be configured from an independently trusted owner identity registry. A valid signature from an untrusted key is not authorization.
2. The HMAC secret must be stored independently of the ledger and its seal. The seal must be exported to independent immutable or access-restricted storage. A locally stored seal and local key do not establish tamper-proof retention. Truncation to an earlier *validly sealed* snapshot cannot be detected without a separately retained checkpoint or sequence registry.
3. The current Garage/AWS uploader uses the existing append-only local JSONL ledger; this increment does **not** integrate automatic sealing into its write path. Do not claim continuous or tamper-proof audit enforcement.
4. The legacy `validate_owner_deletion_approval` function is structural only. Future deletion authorization must call `verify_signed_owner_approval` with a trusted public key, and enforce approval replay prevention and auditable owner-key rotation. There is deliberately no deletion executor.
5. Live AWS/Garage IAM, retention, and concurrency enforcement remain unverified. No Terraform apply or cloud write is included.
6. Delivered gross order value across five marts passed prior user-side read-only reconciliation ($15,419,773.75; zero discrepancies). This does not certify payment settlement, net revenue or refunds.
7. Dashboard/revenue tests (8), recovery/fault-injection tests (18), and full suite (153 passed, 4 Windows symlink privilege skips) passed before this increment. The 9 new tests were verified locally; run the full suite after applying.

## Apply

Extract ZIP preserving paths into the repository root. This increment only adds three files. No existing files or data are overwritten.

## Validate (PowerShell, repository root)

```powershell
python -m pytest tests/test_governance_evidence.py -q
python -m pytest -q -rs
python -m analytics.acceptance_batch_2_4 --db "data/airflow_dev/shopanalysis_airflow.duckdb"
git diff --check
git status --short
```

The reconciliation command is read-only, but run only if that local database exists and the prior acceptance module is installed. `cryptography` must be available in the project environment for the signature tests. If not, install it through your approved dependency-management process; this package does not alter requirements files.

## Acceptance state

- M2: Signed approval verification and audit snapshot integrity have isolated tests; production wiring, replay protection, owner-key governance, independently retained seals, and live backend verification remain open.
- M3: Delivered gross-value cross-mart parity previously verified; broader revenue definitions remain separate.
- M4: Dashboard, recovery and fault-injection unit tests previously verified; live alert delivery and scheduled operations remain unverified.

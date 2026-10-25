# ShopAnalysis — Batch 2–4 integration and closure evidence

## Verified from workstation output (2026-10-24)

- Full regression suite before this increment: **174 passed, 5 skipped**.
- All five skips concern Windows symlink privileges, including one replay-registry test.
- Delivered-order reconciliation: **PASS**, 99,441 orders, 96,478 delivered orders, zero discrepancies.
- Each of the orders/monthly/customer/category/seller marts reports merchandise 13,221,498.11, freight 2,198,275.64, gross order value 15,419,773.75.
- Dashboard/revenue tests: 8 passed; recovery/fault-injection tests: 18 passed.
- Final acceptance gate: `PASS_WITH_LIMITATIONS`.

## This increment

Adds an **offline synthetic exercise**, not an object deletion workflow. It integrates signed-approval verification, one-time SQLite registry consumption, local JSONL audit, HMAC sealing, and seal verification. The six tests use ephemeral keys and temporary paths. The exercise has no CLI or cloud client and cannot delete objects.

### Validation

```powershell
python -m pytest tests/test_offline_governance_exercise.py -q
python -m pytest -q -rs
python -m analytics.final_acceptance_batch_2_4 --db "data/airflow_dev/shopanalysis_airflow.duckdb"
git diff --check
```

The projected suite total is **180 passed, 5 skipped** if no other files change; only workstation output can confirm this.

## Milestone disposition

- **2 — ADR-001 governance:** local proof-of-concept validated; **NOT CLOSED**. Live backend enforcement, distributed replay protection, durable external audit checkpoints, authenticated operational workflow and fault recovery remain unverified. Terraform apply is not authorized.
- **3 — Revenue:** delivered-order gross-value reconciliation **ACCEPTED FOR THIS METRIC ONLY**. Payment settlement and net revenue remain outside the verified scope; no claim of their reconciliation is made.
- **4 — Analytics/observability:** existing unit/integration tests **PASSED**; **NOT FULLY CLOSED**. Live alert delivery and scheduled recovery remain unverified.

## Security and operational boundaries

- **No deletion is implemented or authorized.** Do not use production owner credentials or production registry/audit paths with the synthetic exercise.
- Registry consumption is not atomic with audit writing/sealing. A failure between these steps can consume approval without complete evidence. Never automatically retry. This is not a production authorization transaction.
- A local HMAC seal is only independently trustworthy if the key and seal checkpoint are protected outside the mutable host.
- A local SQLite registry cannot prevent replay across independent hosts.
- Four prior symlink-security tests and one registry symlink test are skipped due to Windows privilege limitations; run in suitable CI before security certification.
- Existing backups, untracked files, databases and object stores must remain untouched. No commits, merges, cloud operations or Terraform apply without separate approval.

## Remaining project closure gates

1. Security architecture review and actual enforcement integration with durable transactional evidence.
2. Payment/net revenue scope decision or separate implemented checks.
3. Live observability and scheduled recovery evidence, if production certification is required.
4. Repository review and authorized Git integration; then Milestones 5–6 acceptance.

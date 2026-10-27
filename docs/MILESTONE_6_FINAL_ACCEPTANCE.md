# ShopAnalysis — Milestone 6 Final Acceptance Record

**Evidence status:** Prepared from operator-reported command outputs through 2026-10-25 UTC. This document is a **local portfolio acceptance record**, not production certification or an attestation of checks not executed.

## Decision

**LOCAL PORTFOLIO ACCEPTANCE: PASS WITH DOCUMENTED LIMITATIONS.** The locally tested engineering and analytics implementation is eligible for portfolio presentation, with explicit limitations below. **PRODUCTION CERTIFICATION: NOT GRANTED.** Repository integration is **PENDING REVIEW/AUTHORIZATION**.

## Verified evidence

| Control | Evidence | Decision |
|---|---|---|
| Regression suite | `python -m pytest -q -rs`: **187 passed, 5 skipped**, no failures (operator output) | PASS for executed tests |
| Skips | Five Windows symlink-permission-dependent tests (approval registry, public aggregate generator x2, public data access x2) | NOT EXECUTED; requires symlink-capable environment |
| Revenue | Read-only reconciliation: **99,441 orders**, **96,478 delivered**; merchandise **$13,221,498.11**, freight **$2,198,275.64**, gross delivered value **$15,419,773.75**. Orders, monthly, customer, category and seller marts match; no discrepancies. | PASS for delivered gross-value parity only |
| Governance | Synthetic signature, audit integrity, replay registry and offline exercise tests passed | PASS for tested offline behaviors only |
| Terraform | `fmt -check` and `validate -no-color` succeeded locally | PASS for source formatting/configuration; not deployment |
| Observability | 18 targeted pipeline recovery/fault-injection tests and 8 dashboard/revenue tests passed in prior runs | PASS for tested local scenarios |
| Performance | DuckDB 1.5.6, Python 3.14.6, Windows 11, DB 121,647,104 bytes, 7 timed repetitions/query + 1 warm-up | MEASURED LOCAL ONLY |
| Delivered KPI query | Median **44.0117000835 ms**, min 42.1144999564 ms, max 45.5964000430 ms | Baseline, no SLA |
| Monthly mart query | Median **0.2705000807 ms**, min 0.2138999989 ms, max 0.3015000839 ms | Baseline, no SLA |
| Whitespace | `git diff --check` emitted LF/CRLF conversion warnings but no whitespace errors | PASS for tracked diff check |

## Milestone disposition

1. **CI / reproducibility:** Prior local regression and CI evidence available; latest CI run on the final uncommitted change set **not verified**.
2. **ADR-001 governance:** Accepted design decision and offline controls validated; deployed retention, owner authorization, durable audit, atomic consumption/audit boundary and backend deletion restrictions **not certified**.
3. **Revenue reconciliation:** **ACCEPTED** for delivered gross merchandise + freight parity. Payment settlement, refunds, net revenue and attribution **not verified**.
4. **Analytics / observability:** **ACCEPTED** for local automated dashboard, cross-mart, recovery and fault-injection tests. Live alert delivery and scheduled recovery **not verified**.
5. **Performance / documentation:** Local benchmark evidence **ACCEPTED**. Final documentation completeness and production performance **not certified**.
6. **Final acceptance:** **PASS WITH LIMITATIONS** for local portfolio scope; repository integration and production certification **OPEN**.

## Explicit limitations and risks

- An offline signed approval verifier and replay registry do **not** authorize or enable object deletion. The approval-consumption and audit-write operations are not one atomic transaction; a crash between them can leave incomplete evidence. No automatic retry should be assumed safe.
- A local JSONL audit ledger and independently generated seal require protected keys, immutable checkpoints and operational retention before claims of durable tamper resistance.
- Local replay prevention is not distributed replay prevention. Concurrent cloud writers, backend IAM policies, bucket lifecycle configuration and live deletion denial have not been demonstrated on deployed systems.
- The acceptance runner without external evidence returns `PASS_WITH_LIMITATIONS` and correctly reports `NOT_VERIFIED` for audit integrity, owner approval, cloud enforcement, replay prevention, settlement, net revenue, live alerting and scheduled recovery.
- Five Windows symlink tests skipped due to missing privileges; run in an authorized symlink-capable CI/Windows environment for complete coverage.
- Benchmark caching, hardware load and comparability were not controlled; no production latency target or cloud-cost claim is established.
- The working tree includes unrelated backups and archived scripts; these must not be staged inadvertently.

## Repository integration boundary

Candidate change set: five modified tracked files plus the new implementation, test and documentation files listed in `docs/MILESTONE_6_REVIEW_MANIFEST.txt`. A reviewer must inspect the diff and independently confirm no credentials, protected datasets, backups or unrelated changes are included. No Git staging, commit, push or merge is authorized by this record.

## Closure checklist

- [x] Full local suite reported: 187 passed, 5 skipped.
- [x] Delivered gross-value reconciliation: five marts, zero discrepancies.
- [x] Local benchmark captured and qualified.
- [x] Governance offline controls tested; limitations recorded.
- [x] Terraform configuration locally validated.
- [ ] Final candidate diff reviewed and approved.
- [ ] Latest CI on final change set verified.
- [ ] Skipped symlink security cases executed in an eligible environment, or risk accepted explicitly.
- [ ] Live governance, alerting and recovery certified if production deployment is in scope.
- [ ] Repository integration separately authorized.

**Disposition:** Local portfolio deliverable may be described as **validated with limitations**, never as production-certified or fully deployed.

## 2026-10-27 local completion addendum

**Final local disposition: COMPLETE / ACCEPTED / CLOSED.** Subsequent full-Olist evidence establishes 231/231 dbt PASS, two successful local Airflow runs (latest 5/5 tasks), 18/18 audit reconciliations, 2/2 RAW integrity checks, 19/19 targeted recovery tests, and 10/10 dashboard/performance tests. The delivered payment-versus-gross difference was approximately 0.0174%, within the defined 0.1% tolerance. Current read-only local DuckDB benchmark medians were 43.2978 ms (delivered KPI) and 0.2730 ms (monthly mart), seven timed repetitions each, cache uncontrolled.

This addendum supersedes earlier local *not yet verified* statements only where these later results apply. It does not certify cloud deployment, live production controls, settlement, refunds, net revenue, or the charter's illustrative USD balances. Historical results and Windows symlink skips remain part of the audit record. See [final closure evidence](PROJECT_CLOSURE_2026-10-27.md).

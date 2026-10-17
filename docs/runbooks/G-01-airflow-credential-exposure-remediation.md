# G-01 — Airflow Credential Exposure Remediation

## Finding

- **Finding ID:** G-01
- **Component:** ShopAnalysis Airflow orchestration
- **Finding:** Credentials committed to public Git history
- **Historical commit:** `75019050c0bc`
- **Affected file:** `orchestration/airflow/.env.example`
- **Remediation date:** 2026-10-17
- **Technical remediation status:** Complete
- **Disposition:** Remediated; historical exposure retained as documented residual risk

## Exposure Assessment

The historical commit contained nonempty values for:

- `AIRFLOW_POSTGRES_PASSWORD`
- `AIRFLOW_SQL_ALCHEMY_CONN`
- `AIRFLOW_JWT_SECRET`

The project owner confirmed that these historical credentials were never deployed or reused in another environment.

The credentials in the operational Airflow `.env` were different from the historical values. The operational credentials were nevertheless rotated as a precaution.

No claim is made that historical Git objects have been removed from the public repository.

## Remediation Actions

1. Created and verified a PostgreSQL pre-rotation backup.
2. Generated replacement PostgreSQL and Airflow JWT credentials.
3. Updated the operational Airflow `.env`.
4. Changed the PostgreSQL `airflow` role password.
5. Recreated the Airflow API server, scheduler, and DAG processor containers with updated configuration.
6. Verified the running Airflow containers use the replacement SQLAlchemy connection and JWT secret.
7. Recreated the PostgreSQL container using the updated environment while preserving its persistent database volume.
8. Removed the successfully exited, pre-rotation `airflow-init` container.
9. Verified the operational `.env` is ignored and untracked by Git.
10. Verified the committed `.env.example` contains empty placeholders for the three affected settings.

## Validation Evidence

| Verification | Result |
|---|---|
| Replacement PostgreSQL password over authenticated TCP connection | PASS |
| Previous PostgreSQL password rejected with authentication failure | PASS |
| Airflow database connectivity after rotation | PASS |
| Airflow scheduler liveness | PASS |
| Airflow DAG processor liveness | PASS |
| Airflow runtime SQLAlchemy connection configuration | PASS |
| Airflow runtime JWT configuration | PASS |
| PostgreSQL data volume preserved during recreation | PASS |
| PostgreSQL container password configuration updated | PASS |
| PostgreSQL healthy after recreation | PASS |
| Airflow API server, scheduler, and DAG processor running | PASS |
| Stale initialization container removed | PASS |
| Operational `.env` ignored and untracked | PASS |
| Committed `.env.example` placeholders empty | PASS |

Verification was performed through the G-01 remediation sequence R1–R12.

## Residual Risk and Limitations

The historical Git commit remains accessible. Sanitizing the current branch does not remove historical Git objects or previously created repository copies.

The project owner's confirmation that the historical credentials were never deployed or reused is an owner attestation, not independent proof of their historical usage.

The completed authentication tests establish revocation of the previous operational PostgreSQL password in the tested local Airflow environment. They do not establish the security state of unrelated environments.

The pre-rotation database backup and environment backup were retained outside the repository. Their retention and eventual secure disposal require separate handling.

## Closure Assessment

The verified local Airflow credential rotation and container cleanup are complete. The committed example configuration is sanitized, and the operational environment file is excluded from Git tracking.

**G-01 disposition: Remediated.**

Formal administrative closure is subject to the project's finding-management and residual-risk acceptance process, if applicable.

No credential values are included in this record.
# ShopAnalysis Milestones 2–4 — Integrated acceptance gate

This increment **adds** a read-only acceptance runner and synthetic tests. It does not alter the existing uploader, Terraform, databases, cloud resources, or Git state. It does not authorize or execute deletion.

## Validation

From the repository root in the activated virtual environment:

```powershell
python -m pytest tests/test_final_acceptance_batch_2_4.py -q
python -m pytest -q -rs
python -m analytics.final_acceptance_batch_2_4 --db "data/airflow_dev/shopanalysis_airflow.duckdb"
```

The acceptance runner opens the DuckDB database read-only via `analytics.acceptance_batch_2_4.inspect`. Its default JSON report does not claim that unprovided security evidence was verified. To save an **additional** report, specify `--output <new-file-path>` with an existing parent directory. Output uses exclusive creation and never overwrites existing files.

Optional *offline* checks: provide `--audit-file`, `--audit-seal`, and `--audit-hmac-env` (the name of an environment variable holding a hex-encoded HMAC key); or `--approval-envelope`, `--trusted-public-key` (raw Ed25519 public-key bytes), `--owner-id`, `--environment`, `--bucket`, `--object-key`, and optionally `--version-id`. Do not paste secret HMAC keys into command history. Never store private signing keys in the repository.

## Acceptance boundaries

- **Milestone 2:** Signed owner approval and audit snapshot integrity can be verified offline when trusted evidence is supplied. A signed approval is **not** replay protection, an authorization to execute deletion, or evidence of actual backend enforcement. Existing uploader does not automatically seal its ledger. Independently protected audit checkpoints and owner-key lifecycle remain outstanding.
- **Milestone 3:** Read-only parity of delivered merchandise, freight, and gross order value across orders, monthly, customer, category and seller marts. Payment settlement, returns, refunds and net revenue are not validated by this gate.
- **Milestone 4:** Cross-mart analytics consistency is validated. Dashboard/recovery/fault-injection tests must be run through pytest; this runner does not prove live alert delivery or scheduled operational recovery.
- **Final:** A `PASS_WITH_LIMITATIONS` report is *not* full milestone closure or production certification. The report explicitly lists unchecked requirements. Four Windows symlink-privilege skips remain separately documented from the user-side regression suite.

Prior user-side evidence: 162 tests passed, 4 skipped; delivered gross order value **$15,419,773.75** with zero discrepancies across five marts. The new increment requires local user-side validation before updating that baseline.

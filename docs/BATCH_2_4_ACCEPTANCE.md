# ShopAnalysis — Combined Milestones 2–4 Acceptance

## Existing baseline (user-reported)
- 149 passed, 4 skipped, no failures; Terraform `fmt -check` and `validate` exit 0.
- ADR-001 governance policy is finalized in local documentation; AWS/Garage deployment and authenticated deletion enforcement remain unverified.

## New cross-mart read-only acceptance check
`analytics/acceptance_batch_2_4.py` compares **delivered** gross merchandise, freight, and gross order values in the order fact against monthly, customer, category, and seller revenue marts. It also checks order-ID uniqueness and arithmetic parity. A discrepancy results in nonzero exit status and a structured exception report.

### Run (existing local mart database; no writes to DB)
```powershell
python -m pytest tests/test_acceptance_batch_2_4.py -q
python -m pytest -q
python -m analytics.acceptance_batch_2_4 --db "data/airflow_dev/shopanalysis_airflow.duckdb"
```

The last command requires `main_marts` tables in the chosen database. If it fails, inspect the exception rather than changing protected data. To save a JSON report, use `--output` with a new file path in an existing directory; this writes only that report file.

## Explicit acceptance limitations
- This is a **first combined-batch increment**, not certification of Milestones 2–4.
- Delivered gross order value is not equivalent to recognized revenue, net revenue, refunds, or payment settlement. Those need explicit business definitions and supporting sources.
- The category/seller marts depend on dimension joins; parity failure may identify dropped rows or model-grain problems.
- Existing audit JSONL is not tamper-proof; owner ID field matching is not authentication.
- AWS/Garage backend behavior, production audit durability, exceptional deletion enforcement, and alerting/recovery execution remain unverified.
- No protected DB mutation, cloud call, Terraform apply, Git operation, or deletion is included.

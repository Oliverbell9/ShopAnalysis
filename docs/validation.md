# Local validation and CI evidence

This guide covers the repository's **synthetic** validation, not real Olist certification, cloud deployment, or a full integration test.

## Python syntax (no dependencies)

From the repository root:

```powershell
python scripts/validate_python_syntax.py
```

This parses Python files under ingestion, data_gen, analytics (if present), orchestration, observability, dashboards, tests, and scripts. It does not execute imports, unit tests, or pipelines.

## Synthetic dbt validation

Use an **isolated clean checkout** or disposable worktree with Python 3.14 and dbt-core 1.12.0 / dbt-duckdb 1.11.0. The fixture generator **refuses to overwrite** `data/shopanalysis_ci.duckdb`; never remove an existing database just to rerun this workflow.

From the repository root:

```powershell
python -m pip install dbt-core==1.12.0 dbt-duckdb==1.11.0
python data_gen/generate_synthetic_raw.py --database data/shopanalysis_ci.duckdb
Push-Location dbt
try {
    dbt parse --no-partial-parse --profiles-dir .
    dbt run --profiles-dir ./ci_profiles --target ci --no-partial-parse
    dbt test --profiles-dir ./ci_profiles --target ci --exclude assert_dim_customer_scd2_controls assert_fct_olist_orders_delivered_metric_controls --no-partial-parse
}
finally {
    Pop-Location
}
```

These commands match the GitHub Actions synthetic dbt scope. The two excluded assertions encode **full Olist dataset-specific totals**, which cannot be expected of the seven-order synthetic fixture. They are not disabled in the dbt project and must be executed separately against a verified full Olist environment before their controls can be certified.

The fixture is synthetic and intentionally contains reconciliation edge cases. Successful dbt CI does not prove raw object-store overwrite protection, cloud RBAC, public-data publication approval, or full-dataset reconciliation.

## CI evidence

GitHub Actions workflow: `.github/workflows/static-ci.yml`.

For each review branch, use the specific workflow run's completed conclusion and individual job steps as evidence. Do not infer a passing run from workflow source alone.

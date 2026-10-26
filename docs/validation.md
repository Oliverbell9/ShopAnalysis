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

## Bash equivalent (Linux/macOS)

Run from the root of a **fresh, disposable checkout**. The CI profile expects `data/shopanalysis_ci.duckdb`; do not overwrite an existing database. Use a new checkout for each fixture run.

```bash
python -m pip install dbt-core==1.12.0 dbt-duckdb==1.11.0
python data_gen/generate_synthetic_raw.py --database data/shopanalysis_ci.duckdb
(
  cd dbt
  dbt parse --no-partial-parse --profiles-dir .
  dbt run --profiles-dir ./ci_profiles --target ci --no-partial-parse
  dbt test --profiles-dir ./ci_profiles --target ci --exclude assert_dim_customer_scd2_controls assert_fct_olist_orders_delivered_metric_controls --no-partial-parse
)
```

The isolated checkout is a documented rerun workaround, **not** a `--force` fixture-generation feature. The fixture generator remains non-overwriting.

## Verified GitHub Actions run

[Static and synthetic CI run #157](https://github.com/Oliverbell9/ShopAnalysis/actions/runs/40344237925) completed with **success** on `main`, commit `e039550727a96486ca1ede963d7625e4d7bc9862`, 2026-10-26. This establishes only the workflow's configured scope, including its two full-Olist test exclusions.

The separately reported **200 passed / 5 skipped** Python tests have not been tied to a specific log and skipped-test explanations. Do not treat that figure as an independently verified run result.

## CI evidence

GitHub Actions workflow: `.github/workflows/static-ci.yml`.

For each review branch, use the specific workflow run's completed conclusion and individual job steps as evidence. Do not infer a passing run from workflow source alone.

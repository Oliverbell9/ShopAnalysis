# ShopAnalysis — Evidence and Scope

**Portfolio milestone concluded; feature development frozen.** This is a scoped portfolio handoff, not certification that every original charter deliverable was built.

## Implemented or available in source

- Governed Olist RAW ingestion entry point, source validation, audit lifecycle, and reconciliation controls: see [governed RAW ingestion](governed_raw_ingestion.md).
- Synthetic dbt/DuckDB workflow and Python test suite: see [validation instructions](validation.md) and [GitHub Actions workflow](../.github/workflows/static-ci.yml).
- AWS S3/IAM Terraform definitions and object-protection uploader source: see [Terraform](../infra/terraform/aws). Source code and a Terraform plan do not prove live deployment or enforcement.

## Objectives not demonstrated by the recorded evidence

- The 0.1% reconciliation target on full Olist data is **unverified**.
- Synthetic CI excludes `assert_dim_customer_scd2_controls` and `assert_fct_olist_orders_delivered_metric_controls`; these require a verified full-Olist environment.
- The $4.8M, $5.1M, and $4.6M departmental revenues are **illustrative USD scenario values**, not measured or currency-converted Olist/UCI outputs.
- The originally envisioned technical report, reconciliation workbook, fault-injection results, executive dashboard, analytical notebooks, defense materials, Snowflake/Airflow operational deployment, and advanced analytics are not certified as delivered by the closure evidence.
- The architecture's observability goals exceed the independently verified runtime evidence; audit records and tests are implemented, but this is not evidence of a production observability service.

## Evidence and reproducibility

The prior completion record reports 200 passed / 5 skipped Python tests and a passing CI run, but does not identify the exact pytest invocation or skipped-test reasons. A later [GitHub Actions run #157](https://github.com/Oliverbell9/ShopAnalysis/actions/runs/40344237925) succeeded on commit `e039550727a96486ca1ede963d7625e4d7bc9862` with synthetic-only coverage. Treat those figures as **historical reports**, not reproducible certification, until linked to the specific commit and run. Follow [validation](validation.md) for the documented synthetic checks.

`requirements.txt` and the workflow both specify Python 3.14, dbt-core 1.12.0, and dbt-duckdb 1.11.0; agreement between configuration files is not independent proof of dependency compatibility.

Terraform's 2-add / 6-change plan indicates existing tracked infrastructure state or imported resources. Its provenance, live account resources, and authorization to apply must be checked separately. No `terraform apply` was authorized by the portfolio closure.

## Architecture and governance decisions

[ADR-001](adr/ADR-001-raw-file-format-partitioning.md) accepts the architecture and governance policy, **not** historical-batch backend enforcement. The local Parquet working landing zone is replaceable; it is not itself immutable historical storage. The seven ADRs were enumerated: ADR-001 is Accepted for architectural policy only; ADR-002 through ADR-007 are Proposed.

## Repository hygiene and licensing

The [gitignore](../.gitignore) excludes `data/raw/*`, `data/parquet/*`, `data/samples/*`, `*.duckdb`, Terraform state, and local secrets. Ignore rules do not prove that files were never tracked; verify with `git ls-files` before public distribution. Dataset redistribution requires a separate license review.

ShopAnalysis source code is licensed under the [MIT License](../LICENSE). Third-party datasets and dependencies are not relicensed.

## Collaboration

An open pull request, [#17](https://github.com/Oliverbell9/ShopAnalysis/pull/17), concerns direct CLI imports. It requires an explicit owner decision to merge or close; this documentation change does not decide its disposition.

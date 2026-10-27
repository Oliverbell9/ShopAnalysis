# ShopAnalysis

**Governed, observable data engineering and analytics portfolio**

**Status: Four-phase Olist local implementation COMPLETE / ACCEPTED / CLOSED (2026-10-27). Portfolio feature development frozen.**

ShopAnalysis demonstrates governed commerce-data ingestion, transformation, lineage, reconciliation, orchestration, automated validation, and analytics using a permanent local architecture built around Parquet, DuckDB, dbt, and Apache Airflow.

## Business scenario

Finance **$4.8M**, Marketing **$5.1M**, and Operations **$4.6M** are hypothetical USD amounts illustrating inconsistent revenue definitions. They are not observed Olist (BRL) or UCI Online Retail II (GBP) balances or currency conversions.

The verified local implementation reconciled delivered-order gross value against recorded delivered payments:

| Metric | Verified local result |
|---|---:|
| Total Olist orders | 99,441 |
| Delivered orders | 96,478 |
| Delivered merchandise value | 13,221,498.11 |
| Delivered freight value | 2,198,275.64 |
| Delivered gross order value | 15,419,773.75 |
| Recorded delivered payments | 15,422,461.77 |
| Absolute payment-versus-gross difference | 2,688.02 |
| Approximate relative difference | 0.0174% |
| Defined comparison tolerance | 0.1% |
| Cross-mart discrepancies | 0 |

Monetary figures are in source monetary units, in the Olist BRL context.

**Acceptance boundary:** The 0.0174% result satisfies the specified delivered-order payment-versus-gross comparison tolerance. It does not establish reconciled net revenue, refund-adjusted revenue, payment settlement, or agreement between the illustrative departmental balances.

## Implemented and evidenced

The following results were recorded for the accepted local implementation:

| Area | Verified evidence |
|---|---|
| Source integrity | Nine original Olist CSVs; SHA-256 and source/RAW row-count checks passed |
| Ingestion | Olist-to-Parquet processing, governed DuckDB RAW loading, source lineage, and batch controls |
| dbt transformations | 231 full-Olist tests passed; zero warnings, errors, or skips |
| Data modeling | Staging, intermediate, marts, and SCD Type 2 customer-history controls |
| Reconciliation | Delivered financial comparison within 0.1% tolerance; zero cross-mart discrepancies |
| Local Airflow | Two successful runs; latest run completed 5/5 DAG tasks |
| Audit controls | 18/18 reconciliations and 2/2 RAW integrity checks passed |
| Recovery testing | 19/19 isolated recovery and fault-injection tests passed |
| Dashboard/performance tests | 10/10 tests passed |
| Local query benchmarks | Read-only DuckDB measurements completed; no production SLA established |

The local validation results are separate from GitHub Actions' synthetic CI coverage.

### GitHub Actions evidence

[GitHub Actions run #157](https://github.com/Oliverbell9/ShopAnalysis/actions/runs/40344237925) succeeded on commit `e039550727a96486ca1ede963d7625e4d7bc9862` on October 26, 2026.

That run uses an isolated seven-order synthetic fixture and excludes two full-Olist assertions. Its success does not independently establish the 231-test full-data result.

The previously reported **200 passed / 5 skipped** Python result remains historical evidence without an archived invocation and complete skip-reason log. Historical Windows symlink-dependent skips are not retroactively represented as passes.

See [validation and reproducibility](docs/validation.md) and the [final closure evidence](docs/PROJECT_CLOSURE_2026-10-27.md).

## Architecture and data

### Accepted permanent local implementation

```text
Nine Olist CSV source files
           |
           v
Source integrity validation
           |
           v
     Local Parquet
           |
           v
   Governed DuckDB RAW
           |
           v
       dbt STAGING
           |
           v
     dbt INTERMEDIATE
           |
           v
        dbt MARTS
           |
           v
 Reconciliation and analytics
           |
           v
   Local dashboard metrics
```

Apache Airflow provides local workflow orchestration. Audit and recovery controls support validation, traceability, and isolated failure testing.


### Reference cloud architecture

```text
Source Systems
      |
      v
    AWS S3
      |
      v
 Snowflake RAW
      |
      v
 dbt Transformations
      |
      v
 Analytical Marts
      |
      v
 Semantic / BI Analytics
```

AWS S3/IAM Terraform definitions and uploader components exist in the repository. Terraform plans and source-code tests do not establish deployed infrastructure, live retention enforcement, or authorized infrastructure changes.

### Source scope

The accepted full-data implementation is based on the nine Olist CSV source tables.

UCI Online Retail II, synthetic CRM/marketing data, and optional DataCo integration belong to the broader reference design and are not represented as fully integrated, certified local sources.

## Data quality, reconciliation, and recovery

The accepted local scope includes:

- Source-file integrity and RAW row-count parity checks.
- Full-data dbt model and assertion testing.
- Customer SCD Type 2 controls.
- Delivered-order financial reconciliation.
- Cross-mart consistency checks.
- Batch-level audit and RAW integrity controls.
- Isolated fault-injection and recovery tests.
- Dashboard metric and performance regression tests.

These results establish the tested local behavior. They do not prove automatic production recovery, live alert delivery, or cloud infrastructure enforcement.

## Local performance baseline

A read-only benchmark was executed against DuckDB 1.5.6 on October 27, 2026, using seven timed repetitions and one warm-up per query.

| Query | Median latency |
|---|---:|
| Delivered-order KPI | 43.2978 ms |
| Monthly analytical mart | 0.2730 ms |

Cache conditions and workstation load were not controlled.

These measurements are local performance baselines, not production service-level agreements or evidence of Snowflake warehouse cost and performance.

## Reproduce the evidenced validation

Project dependencies are specified in [requirements.txt](requirements.txt).

The GitHub Actions workflow specifies Python 3.14, `dbt-core==1.12.0`, and `dbt-duckdb==1.11.0`. These configuration values are not a guarantee of compatibility across every local environment.

See [docs/validation.md](docs/validation.md) for PowerShell and bash instructions, synthetic fixture isolation, and CI exclusions.

The October 27 full-Olist execution results are recorded separately in the [final local closure evidence](docs/PROJECT_CLOSURE_2026-10-27.md). Reproducing those results requires the applicable full-data environment and inputs; running synthetic CI alone is insufficient.

## Repository layout

The following is a top-level map, not an exhaustive directory inventory:

```text
ShopAnalysis/
├── .github/workflows/        # static and synthetic CI
├── analytics/                # analytics source and validation
├── dashboards/               # dashboard-related source
├── data/                     # manifests and ignored local data
├── data_gen/                 # synthetic fixture generator
├── dbt/                      # transformations and tests
├── docs/
│   ├── adr/                  # ADR-001 through ADR-007
│   ├── evidence_and_scope.md
│   ├── portfolio_completion.md
│   ├── PROJECT_CLOSURE_2026-10-27.md
│   ├── technical_closure_report.md
│   ├── validation.md
│   └── governed_raw_ingestion.md
├── infra/terraform/          # AWS and Snowflake definitions
├── ingestion/                # ingestion and object-store code
├── observability/            # audit and recovery components
├── orchestration/airflow/    # Airflow-related files
├── scripts/                  # command-line utilities
├── tests/                    # regression tests
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Architecture decision records

Seven architecture decision records are maintained in [docs/adr](docs/adr/).

**ADR-001** is Accepted for architectural and governance policy only. Its backend historical-retention enforcement is not certified.

**ADR-002 through ADR-007** remain Proposed. A proposed architectural decision is not evidence of deployed operational behavior.

## Governance, licensing, and publication

The repository contains a published [MIT License](LICENSE) for project source code. Third-party datasets, including Olist and UCI, retain their own terms. The project's MIT license does not authorize redistribution of those datasets.

The repository's [.gitignore](.gitignore) excludes local datasets, database files, secrets, and Terraform state. Ignore rules do not replace a repository-history, licensing, or credential-disclosure audit.

The previously reviewed Terraform plan showed **2 additions, 6 changes, and 0 deletions**. Its existing-state provenance has not been established, and the portfolio closure did not authorize `terraform apply`.

## Project completion and repository integration

The historical portfolio milestone was concluded on October 25, 2026, with feature development frozen.

Subsequent full-Olist evidence supported acceptance and closure of the bounded four-phase local implementation on October 27, 2026.

The earlier local documentation commit `3d5d478` remains separate and is not represented as integrated into GitHub's `main`.

## Documentation

- [October 27 local closure and evidence](docs/PROJECT_CLOSURE_2026-10-27.md)
- [Technical closure report](docs/technical_closure_report.md)
- [Milestone 6 final acceptance](docs/MILESTONE_6_FINAL_ACCEPTANCE.md)
- [Evidence and scope](docs/evidence_and_scope.md)
- [Validation and reproducibility](docs/validation.md)
- [Governed RAW ingestion](docs/governed_raw_ingestion.md)
- [Portfolio completion record](docs/portfolio_completion.md)
- [Architecture decisions](docs/adr/)
- [Project charter](docs/charter.md)

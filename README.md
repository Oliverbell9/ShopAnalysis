# ShopAnalysis

**Governed RAW ingestion and analytics engineering portfolio**

**Status: Portfolio milestone concluded; feature development frozen.** This means the evidenced engineering foundation is delivered—not that the original end-to-end analytics platform or its business targets were certified.

## Business scenario

Finance **$4.8M**, Marketing **$5.1M**, and Operations **$4.6M** are **hypothetical USD amounts** illustrating inconsistent revenue definitions. They are **not** Olist (BRL) or UCI Online Retail II (GBP) observations or conversions. The proposed target of reconciling full-source business metrics within **0.1% remains unverified**.

## Implemented and evidenced

- Python/Olist-to-Parquet ingestion, source contracts, governed DuckDB RAW loading, batch audit and reconciliation controls; see [governed ingestion](docs/governed_raw_ingestion.md).
- dbt/DuckDB synthetic transformations and tests. The seven-order CI fixture does **not** validate full-Olist controls; see [validation](docs/validation.md).
- GitHub Actions static and synthetic CI. [Run #157](https://github.com/Oliverbell9/ShopAnalysis/actions/runs/40344237925) succeeded on commit `e039550727a96486ca1ede963d7625e4d7bc9862` (2026-10-26).
- Terraform AWS S3/IAM definitions and uploader code. A Terraform plan and source files **do not establish** deployed retention enforcement or authorized infrastructure changes.
- Documentation, architecture decisions, regression tests, and MIT-licensed project source code.

## Designed but not verified as delivered

The broader **reference architecture** connects S3 → Snowflake RAW → dbt staging/intermediate/marts → semantic/BI analytics; a local reference design connects Parquet → DuckDB → dbt → analytics. Airflow scheduling, complete Snowflake deployment, production observability, masking/RBAC enforcement, full historical-batch protection, cost/performance studies, executive dashboards, CLV/forecasting, and end-to-end revenue reconciliation are **not certified** by the recorded evidence.

The original deliverables list also contemplated a technical report, reconciliation workbook, fault-injection results, benchmark results, notebooks, and defense materials. Their completion has **not** been established. These are **not** claims of delivered artifacts.

## Outside the concluded milestone

No further feature development, cloud deployment, full-data certification, or new analytics deliverable is authorized by the portfolio closure. Any future implementation requires a separately scoped decision.

## Architecture and data

- **Local implementation:** Olist CSV inputs → verified Parquet → audited DuckDB RAW; synthetic dbt validation.
- **Reference cloud design:** AWS S3 → Snowflake → dbt → BI/analytics.
- **Source scope:** Olist is the main implemented ingestion contract; UCI, synthetic CRM/marketing, and optional DataCo are broader design candidates, not all confirmed integrated sources.
- **Lineage:** local source hashes and batch IDs are implemented; protected historical retention across live object stores is not certified. The replaceable local Parquet landing zone is not immutable archival storage.
- **Observability:** audit and error-handling components exist; no independently certified production monitoring service is claimed.

## Reproduce the evidenced validation

Requirements are pinned in [requirements.txt](requirements.txt). The CI workflow specifies Python 3.14, `dbt-core==1.12.0`, and `dbt-duckdb==1.11.0`. These are the versions used by the workflow, not a general cross-platform compatibility guarantee.

See [docs/validation.md](docs/validation.md) for **PowerShell and bash** commands, isolated fixture paths, and the two excluded full-Olist assertions. A passing synthetic CI run does not certify full-data metric controls.

## Repository layout

The following is a **top-level map**, not an exhaustive directory inventory:

```text
ShopAnalysis/
├── .github/workflows/        # static and synthetic CI
├── analytics/                # analytics source and validation
├── dashboards/               # dashboard-related source
├── data/                     # manifests and ignored local landing areas
├── data_gen/                 # synthetic fixture generator
├── dbt/                      # transformations and tests
├── docs/
│   ├── adr/                 # ADR-001 through ADR-007
│   ├── portfolio_completion.md
│   ├── evidence_and_scope.md
│   ├── validation.md
│   └── governed_raw_ingestion.md
├── infra/terraform/          # AWS and Snowflake definitions
├── ingestion/                # ingestion and object-store code
├── observability/            # audit/observability source
├── orchestration/airflow/    # Airflow-related files
├── scripts/                  # command-line utilities
├── tests/                    # regression tests
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Architecture decision records

There are **seven ADRs** in [docs/adr](docs/adr/). **ADR-001** is **Accepted for architectural and governance policy only**; its backend retention enforcement is **not certified**. **ADR-002 through ADR-007 are Proposed**. Proposed decisions are not represented as operationally implemented.

## Governance and publication

- The current Git tree tracks only `.gitkeep` files in `data/raw/`, `data/parquet/`, and `data/samples/`; it contains no tracked `.duckdb` or Terraform state files. This does not audit historical commits.
- The [.gitignore](.gitignore) excludes local data, database files, secrets, and Terraform state. It does not replace a repository history or data-licensing audit.
- Source code is [MIT licensed](LICENSE). Third-party datasets, including Olist and UCI, retain separate terms; the project MIT license does **not** authorize their redistribution.
- The reported **200 passed / 5 skipped** Python result lacks an identified invocation and skip-reason log. Treat it as historical, not independently anchored CI evidence.
- The Terraform **2 additions / 6 changes / 0 deletions** plan implies existing state or imported resources; state provenance has not been verified. No `terraform apply` was authorized by portfolio closure.

## Documentation

- [Evidence and scope](docs/evidence_and_scope.md)
- [Validation and reproducibility](docs/validation.md)
- [Governed RAW ingestion](docs/governed_raw_ingestion.md)
- [Portfolio completion record](docs/portfolio_completion.md)
- [Architecture decisions](docs/adr/)
- [Project charter](docs/charter.md)

**Collaboration:** [PR #17](https://github.com/Oliverbell9/ShopAnalysis/pull/17) remains open pending an explicit owner merge/close decision. The repository uses review branches and pull requests; no claim of direct-to-main-only development is made.

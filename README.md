# ShopAnalysis

**A Governed, Observable Analytics Platform**

ShopAnalysis is an end-to-end data engineering and analytics portfolio project that demonstrates how a modern analytics platform can ingest, transform, govern, reconcile, orchestrate, observe, and analyze commerce data.

The project is built around a realistic business problem: different business functions report different revenue figures because they use inconsistent metric definitions, different event-time versus booking-time treatments, and unreconciled source systems.

| Business Function | Reported Revenue |
|---|---:|
| Finance | $4.8M |
| Marketing | $5.1M |
| Operations | $4.6M |

The objective is not simply to produce another revenue number. ShopAnalysis builds the engineering, reconciliation, governance, and observability framework required to explain the differences and establish reproducible, governed metrics.

---

## Project Objectives

ShopAnalysis is designed to:

- reconcile key business metrics to within 0.1%;
- build reproducible and idempotent ingestion and transformation pipelines;
- implement source contracts and automated data-quality controls;
- maintain explicit lineage from source files through analytical marts;
- implement dimensional modeling and SCD Type 2 history;
- protect personally identifiable information (PII) through governed access controls;
- orchestrate production-style data workflows;
- implement automated CI/CD;
- measure warehouse cost and query performance;
- deliberately inject and detect realistic data-quality failures;
- build and validate advanced analytical models;
- preserve a permanently reproducible implementation after temporary cloud resources expire.

---

## Architecture

ShopAnalysis uses two complementary implementations.

### Reference Cloud Architecture

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
 dbt STAGING
      |
      v
dbt INTERMEDIATE
      |
      v
  dbt MARTS
      |
      v
Semantic / Metrics Layer
      |
      v
BI + Analytics
```

The reference cloud implementation demonstrates:

- AWS S3 and IAM;
- Terraform infrastructure as code;
- Snowflake storage integrations and external stages;
- `COPY INTO` ingestion;
- Snowpipe evaluation;
- DEV / CI / PROD environment separation;
- role-based access control;
- PII masking and row-access policies;
- resource monitors;
- query history;
- warehouse cost and performance analysis.

### Permanent Portfolio Architecture

```text
Source Systems
      |
      v
Local Files / Garage
      |
      v
    Parquet
      |
      v
  DuckDB RAW
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
Semantic / Metrics Layer
      |
      v
BI + Analytics
```

The permanent implementation is designed to remain runnable without an active Snowflake or AWS subscription.

Apache Airflow provides workflow orchestration, while GitHub Actions provides CI/CD.

The dbt transformation design will remain as warehouse-neutral as practical, with Snowflake-specific behavior isolated where required.

---

## Technology Stack

| Area | Technology |
|---|---|
| Cloud Object Storage | AWS S3 |
| Cloud Data Warehouse | Snowflake |
| Local Object Storage | Garage / local files |
| Permanent Local Warehouse | DuckDB |
| Analytical File Format | Parquet |
| Transformation | dbt |
| Orchestration | Apache Airflow |
| Infrastructure as Code | Terraform |
| CI/CD | GitHub Actions |
| Programming | Python |
| Version Control | Git / GitHub |
| BI / Semantic Layer | To be finalized |

---

## Data Sources

Planned source data includes:

- Olist;
- UCI Online Retail II;
- seeded synthetic CRM data;
- seeded synthetic marketing data;
- optional DataCo data where appropriate.

Synthetic sources will contain known ground truth so that reconciliation and data-quality behavior can be objectively validated.

---

## Raw Data and Lineage

The planned cloud landing convention is:

```text
raw/<source>/<entity>/ingest_date=YYYY-MM-DD/part-*.parquet
```

Raw data is treated as immutable.

Snowflake RAW ingestion will preserve lineage metadata such as:

- `_source_file`
- `_file_row_number`
- `_loaded_at`
- `_batch_id`

The ingestion design will emphasize idempotency, replayability, traceability, and reconciliation.

---

## Source Contracts

Source contracts will document information such as:

- owner;
- ingestion cadence;
- primary key;
- expected volume;
- null policy;
- PII classification;
- SLA.

Contracts are maintained as version-controlled project artifacts.

---

## dbt Transformation Layers

### STAGING

Source-aligned models responsible for:

- renaming;
- type casting;
- standardization;
- deduplication;
- basic source cleanup.

Business joins are intentionally excluded from this layer.

### INTERMEDIATE

Reusable business logic including:

- entity resolution;
- cross-source transformations;
- currency handling;
- reusable business rules.

### MARTS

Governed analytical models containing:

- conformed dimensions;
- fact tables;
- model contracts;
- governed business metrics.

---

## Planned Dimensional Model

### Facts

- `fct_orders`
- `fct_order_items`
- `fct_payments`
- `fct_refunds`
- `fct_shipments`
- `fct_marketing_touches`
- `fct_ad_spend_daily`

### Dimensions

- `dim_customer` — SCD Type 2
- `dim_product`
- `dim_seller`
- `dim_date`
- `dim_geography`
- `dim_campaign`

### Bridge

- `bridge_order_campaign`

---

## Governed Metrics

Initial governed metrics include:

- Gross Revenue
- Net Revenue
- Average Order Value (AOV)
- Refund Rate
- On-Time Delivery
- Customer Acquisition Cost (CAC)

Metric definitions and reconciliation logic will be maintained as version-controlled artifacts.

A dedicated reconciliation process will explain the differences between the reference Finance, Marketing, and Operations revenue figures rather than simply replacing them with an unexplained consolidated number.

---

## Data Quality and Fault Injection

ShopAnalysis includes automated quality controls and deliberate fault injection.

Planned fault scenarios include:

- duplicate records;
- late-arriving data;
- schema drift;
- orphan keys;
- null keys;
- negative quantities;
- cancellations;
- timezone inconsistencies;
- currency inconsistencies;
- backfilled corrections.

The objective is to demonstrate whether the platform can detect, explain, and recover from realistic data failures.

---

## Governance and Security

The reference implementation will demonstrate:

- role-based access control;
- least-privilege access;
- PII classification;
- masking policies;
- row-access policies where required;
- email pseudonymization;
- environment isolation;
- documentation and auditability.

No production credentials, secrets, private keys, account-specific infrastructure identifiers, or raw PII belong in this public repository.

Local credentials must be supplied through environment variables or other secure mechanisms and must never be committed.

---

## Orchestration

Apache Airflow is responsible for workflow orchestration, including:

- dependencies;
- scheduling;
- retries;
- backoff;
- SLA handling;
- backfills.

dbt remains responsible for analytical transformation logic, model dependencies, tests, contracts, and documentation.

This separation will be formally documented in ADR-006.

---

## CI/CD

GitHub Actions will progressively validate:

- Python code;
- YAML;
- SQL;
- dbt parsing;
- dbt compilation;
- dbt tests;
- infrastructure code;
- deployment readiness.

The project follows a trunk-based development approach with automated validation before deployment.

---

## Cost and Performance

The Snowflake implementation will capture evidence for:

- query history;
- query tags;
- credit consumption;
- warehouse sizing;
- full versus incremental transformations;
- applicable dynamic processing approaches;
- scaling behavior;
- pruning and clustering behavior;
- resource-monitor behavior.

Performance experiments will evaluate appropriate warehouse and materialization strategies across increasing data volumes.

Benchmark results will be retained as project evidence so that the analysis remains available after temporary cloud resources are removed.

---

## Advanced Analytics

Planned analytical work includes:

- customer lifetime value;
- retention and survival analysis;
- marketing attribution;
- forecasting;
- late-delivery prediction;
- anomaly detection.

Candidate techniques include BG/NBD and Gamma-Gamma modeling for CLV, survival methods for retention, multiple attribution approaches, predictive modeling for late delivery, and anomaly-detection methods.

Analytical models must include explicit validation rather than presenting model output alone.

---

## Repository Structure

```text
ShopAnalysis/
|
|-- .github/
|   `-- workflows/
|
|-- analytics/
|   |-- models/
|   |-- notebooks/
|   `-- validation/
|
|-- dashboards/
|
|-- data/
|   |-- manifests/
|   |-- parquet/
|   |-- raw/
|   `-- samples/
|
|-- data_gen/
|   |-- config/
|   |-- fault_injection/
|   `-- generator/
|
|-- dbt/
|   |-- macros/
|   |-- models/
|   |   |-- staging/
|   |   |-- intermediate/
|   |   `-- marts/
|   |-- seeds/
|   |-- snapshots/
|   |-- tests/
|   `-- unit_tests/
|
|-- docs/
|   |-- adr/
|   |-- architecture/
|   |-- data_model/
|   |-- metrics/
|   |-- report/
|   |-- runbooks/
|   |-- source_contracts/
|   `-- charter.md
|
|-- infra/
|   `-- terraform/
|       |-- aws/
|       `-- snowflake/
|
|-- ingestion/
|   |-- copy_scripts/
|   |-- file_formats/
|   |-- reconciliation/
|   `-- stages/
|
|-- orchestration/
|   `-- dags/
|
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|-- README.md
`-- requirements.txt
```

---

## Architecture Decision Records

The project maintains formal Architecture Decision Records for major technical decisions:

1. **ADR-001** — Raw File Format and Partitioning
2. **ADR-002** — Ingestion Method
3. **ADR-003** — Environment Strategy
4. **ADR-004** — dbt Materialization Policy
5. **ADR-005** — Dimensional Modeling and SCD Strategy
6. **ADR-006** — Airflow / dbt Orchestration Boundary
7. **ADR-007** — RBAC and Access Model

ADRs begin in `Proposed` status and move to `Accepted` only after the decision, rationale, consequences, and supporting evidence are documented.

---

## Reproducibility

The project is designed so that another developer can eventually reproduce the platform from version-controlled artifacts.

Local secrets are supplied through environment variables and are never committed.

Use:

```text
.env.example
```

as the template for local configuration.

The permanent DuckDB/Garage implementation is intended to preserve a runnable version of the platform even after temporary AWS and Snowflake resources are unavailable.

---

## Public Repository Safety

This repository is intended to be public.

The following must not be committed:

- `.env`;
- passwords;
- API keys;
- AWS credentials;
- Snowflake credentials;
- private keys;
- Terraform state containing sensitive values;
- raw PII;
- personal/local notes;
- local virtual environments;
- machine-specific paths or identifiers.

The repository's `.gitignore` provides an initial safeguard, but files must still be reviewed before commits are pushed publicly.

---

## Primary Deliverables

The completed project is expected to include:

- a reproducible public repository;
- at least seven ADRs;
- a technical report;
- a revenue reconciliation workbook;
- data-quality and fault-injection results;
- cost/performance benchmark results;
- an executive dashboard;
- analytical notebooks;
- documented runbooks;
- project defense materials.

---

## Project Status

**Current Phase:** Foundation and environment setup.

Completed foundation work currently includes:

- repository structure;
- Python virtual environment;
- Git repository initialization;
- public-repository `.gitignore` controls;
- environment-variable template;
- project charter;
- initial seven-ADR framework.

Infrastructure provisioning, source acquisition, ingestion, transformation, orchestration, analytics, and dashboards will be added progressively.

---

## Documentation

Project documentation is maintained under `docs/`.

Key locations include:

- Project charter: `docs/charter.md`
- Architecture decisions: `docs/adr/`
- Architecture documentation: `docs/architecture/`
- Source contracts: `docs/source_contracts/`
- Metric specifications: `docs/metrics/`
- Data-model documentation: `docs/data_model/`
- Runbooks: `docs/runbooks/`
- Technical report: `docs/report/`

---

## License

A license has not yet been selected.

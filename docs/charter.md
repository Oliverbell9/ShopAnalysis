# ShopAnalysis Project Charter

## Project Title

**ShopAnalysis: A Governed, Observable Analytics Platform**

## Purpose

ShopAnalysis is a graduate/professional data engineering and analytics project designed to build a reproducible, governed, observable, and cost-aware analytics platform.

The platform addresses a realistic enterprise problem in which different business functions report conflicting revenue figures because of inconsistent metric definitions, event-time versus booking-time treatment, and unreconciled source systems.

The reference discrepancy is:

- Finance: $4.8M
- Marketing: $5.1M
- Operations: $4.6M

The project will reconcile these figures and establish governed definitions that produce consistent, explainable analytics.

## Core Objectives

1. Reconcile key business metrics to within 0.1%.
2. Build reproducible and idempotent ingestion and transformation pipelines.
3. Establish trustworthy data through tests, contracts, and reconciliation.
4. Govern personally identifiable information (PII) through access controls and masking.
5. Measure and manage warehouse cost and performance.
6. Build validated analytical models and business metrics.
7. Provide an observable and orchestrated production-style data platform.
8. Preserve a permanently reproducible portfolio implementation after cloud trials expire.

## Architecture Strategy

ShopAnalysis uses a dual implementation strategy.

### Reference Cloud Architecture

Sources
→ AWS S3
→ Snowflake RAW
→ dbt STAGING
→ dbt INTERMEDIATE
→ dbt MARTS
→ Semantic / Metrics Layer
→ BI and Analytics

The cloud implementation demonstrates:

- AWS S3 and IAM
- Terraform infrastructure as code
- Snowflake storage integrations and stages
- COPY INTO ingestion
- Snowpipe evaluation
- DEV / CI / PROD environment separation
- RBAC
- PII masking and row-access policies
- resource monitors
- query history
- warehouse cost and performance analysis

### Permanent Portfolio Architecture

Sources
→ Local Files / Garage
→ Parquet
→ DuckDB RAW
→ dbt STAGING
→ dbt INTERMEDIATE
→ dbt MARTS
→ Semantic / Metrics Layer
→ BI and Analytics

This implementation remains runnable without an active Snowflake or AWS subscription.

Apache Airflow provides workflow orchestration and GitHub Actions provides CI/CD.

## Data Sources

Planned source data includes:

- Olist
- UCI Online Retail II
- seeded synthetic CRM and marketing data with known ground truth
- optional DataCo data where appropriate

## Data Quality and Fault Injection

The project will deliberately test failure conditions including:

- duplicate records
- late-arriving data
- schema drift
- orphan keys
- null keys
- negative quantities and cancellations
- timezone inconsistencies
- currency inconsistencies
- backfilled corrections

## Data Engineering Principles

The platform will follow these principles:

- immutable raw data
- idempotent ingestion
- explicit lineage
- separation of ingestion, transformation, and analytics
- source contracts
- everything-as-code
- reproducible environments
- governed access
- automated testing
- observable pipelines

## dbt Transformation Layers

### STAGING

- one-to-one source models
- renaming
- casting
- standardization
- deduplication
- no business joins

### INTERMEDIATE

- reusable business logic
- entity resolution
- currency handling
- cross-source transformations

### MARTS

- conformed dimensions
- business facts
- governed metrics
- model contracts

## Dimensional Model

Planned fact tables include:

- fct_orders
- fct_order_items
- fct_payments
- fct_refunds
- fct_shipments
- fct_marketing_touches
- fct_ad_spend_daily

Planned dimensions include:

- dim_customer (SCD Type 2)
- dim_product
- dim_seller
- dim_date
- dim_geography
- dim_campaign

Planned bridge:

- bridge_order_campaign

## Governed Metrics

Initial governed metrics include:

- gross revenue
- net revenue
- average order value (AOV)
- refund rate
- on-time delivery
- customer acquisition cost (CAC)

Metric definitions will be documented and reconciled across source systems and business interpretations.

## Governance

The platform will implement:

- role-based access control
- PII classification
- masking policies
- row-access policies where required
- pseudonymization of email
- auditability
- documented ownership
- documented data contracts

## Orchestration and CI/CD

Apache Airflow will manage data workflows, including:

- dependencies
- retries
- exponential backoff where appropriate
- SLA handling
- backfills

GitHub Actions will support:

- linting
- YAML validation
- dbt parsing and compilation
- automated testing
- slim CI where applicable
- controlled deployment

## Cost and Performance

The project will evaluate:

- Snowflake query history
- query tags
- credit consumption
- warehouse sizes from XS through L where justified
- full versus incremental transformations
- dynamic processing approaches where applicable
- data volume scaling
- partition pruning / clustering behavior
- resource monitors

## Advanced Analytics

Planned analytical work includes:

- customer lifetime value
- retention / survival analysis
- marketing attribution
- forecasting
- late-delivery prediction
- anomaly detection

Analytical models must include explicit validation rather than model output alone.

## Architecture Decision Records

At minimum, the following ADRs will be maintained:

1. ADR-001 — Raw File Format and Partitioning
2. ADR-002 — Ingestion Method
3. ADR-003 — Environment Strategy
4. ADR-004 — dbt Materialization Policy
5. ADR-005 — Dimensional Modeling and SCD Strategy
6. ADR-006 — Airflow / dbt Orchestration Boundary
7. ADR-007 — RBAC and Access Model

## Primary Deliverables

The completed project will include:

- reproducible source repository
- at least seven ADRs
- technical report
- revenue reconciliation workbook
- data-quality and fault-injection results
- cost/performance benchmark results
- executive dashboard
- analytical notebooks
- documented runbooks
- project defense materials

## Success Criteria

ShopAnalysis is successful when the platform can demonstrate that:

1. conflicting business metrics can be reconciled and explained;
2. ingestion and transformation are reproducible and idempotent;
3. data-quality failures are detected systematically;
4. governed metrics are consistent across analytical consumers;
5. PII is protected through explicit governance controls;
6. pipeline execution is observable and recoverable;
7. infrastructure and transformations are represented as code;
8. cloud cost and performance behavior are measured;
9. analytical outputs are validated;
10. the permanent implementation remains reproducible after cloud trial resources are unavailable.

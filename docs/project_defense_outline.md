# ShopAnalysis — Project Defense Outline (Draft)

**Audience:** Data engineering hiring panel / technical reviewers  
**Status:** Presentation script; no unsupported deployment or benchmark claims

## Slide 1 — Problem and decision
Different revenue definitions, recognition clocks, and unreconciled sources create conflicting reporting. The three business-unit dollar figures in the charter are illustrative.

## Slide 2 — Dual architecture
Reference: S3 → Snowflake RAW → dbt → analytics. Permanent: local files / Garage → Parquet → DuckDB RAW → dbt → analytics. Airflow orchestration and GitHub Actions CI are defined in source.

## Slide 3 — Trust boundaries
Source SHA-256 verification, lineage, batch identity, reconciled marts, and explicit access boundaries. Historical batch protection is under review; do not claim cloud immutability.

## Slide 4 — Dimensional model
Explain `dim_customer` SCD2 effective dating, order-grain `fct_olist_orders`, item-grain facts, and revenue marts. Show an actual dbt lineage screenshot only after generating it.

## Slide 5 — Governed revenue
Separate delivered merchandise, freight, gross order value, payment value, and unknown net revenue. Explain reconciliation categories and eight historically documented timestamp exceptions.

## Slide 6 — Validation and failure modes
Demonstrate synthetic fixture tests and fault-injection evidence. Mark all unexecuted scenarios as pending.

## Slide 7 — Security and publication
Public aggregate-only design; source data licensing and release approvals are still pending.

## Slide 8 — Performance and cost
Show measured DuckDB benchmark results only after running `analytics/benchmark_local.py`. Snowflake credits and warehouse comparisons require actual cloud evidence.

## Slide 9 — Engineering tradeoffs
Local portability vs. cloud representativeness, replaceable local landing vs. protected object history, CI fixture scope vs. full-dataset certification.

## Slide 10 — Open items and roadmap
Unit tests, full Olist reconciliation, workbook, advanced models, fault injection, benchmark evidence, governance review, and authorized deployment.

## Defense rule
Never turn planned architecture, mock-test behavior, or documented control totals into claims of successful production execution.

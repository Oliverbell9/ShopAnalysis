# Full Olist evidence gate (read-only)

**Status: executed by the local operator against the full Olist mart on 2026-10-22; selected financial and historical controls passed.** This is user-reported execution evidence, not a GitHub Actions full-data run.

The permanent GitHub CI uses a seven-order synthetic fixture. A passing CI run is not evidence of full Olist monetary totals, completeness, or cloud controls.

Run the gate from the repository root against an **existing** local DuckDB database with a built `main_marts.fct_olist_orders` table:

```powershell
python analytics/validate_full_olist.py --db "C:\path\to\existing\shopanalysis.duckdb" --compare-documented-controls
```

The example path is a placeholder; use the actual verified path. The script connects with `read_only=True`, returns only aggregate counts and amounts, and does not create files or query cloud services. It checks order-grain uniqueness, NULL order IDs, delivered partition completeness, NULL monetary values, order-level and aggregate monetary parity, and optionally compares delivered totals against the **historically documented** controls in `docs/metrics/revenue.md`. Comparison is opt-in to avoid misrepresenting a small fixture as a full-data validation.

**Documented historical controls, not measurements made by this update:** 96,478 delivered orders; merchandise 13,221,498.11; freight 2,198,275.64; gross 15,419,773.75; delivered payment 15,422,461.77; eight delivery-timestamp exceptions.

A PASS certifies only the checks performed against the specific database supplied. It does not certify input hashes, source row completeness, SCD2 chronology, refund/net revenue, payment-difference causes, RBAC, immutability, licensing, or deployment. Retain the run's timestamp, local DuckDB version, source manifest, dbt invocation and result, and exact database path in a **private** evidence log. Do not publish source rows or credentials.

Run the existing full-data dbt assertions separately, using the appropriate authorized full-data profile and target; the synthetic CI deliberately excludes those assertions. Do not use the synthetic target for full-data certification.

## Missing-payment classification

A delivered order with non-NULL merchandise, freight and gross amounts may legitimately have no matching payment record in the loaded source. The gate reports `classified_missing_payments` separately and does not fail **solely** when `payment_value`, `payment_record_count` and `payment_type_count` are all NULL and `reconciliation_status = 'missing_payment'`. An unclassified NULL payment or an inconsistent `missing_payment` status fails. This is a classification rule, **not** proof that every upstream payment is complete; independently verify raw payment rows and source provenance before interpreting exceptions.

For the investigated order `bfbd0f9bdef84302105ad712db648a6c`, the local operator reported zero matching rows in raw, staging and intermediate payment tables, while the mart retained 134.97 merchandise, 8.49 freight, 143.46 gross and a NULL payment. The findings are user-reported local diagnostic evidence, not a GitHub CI full-data result.

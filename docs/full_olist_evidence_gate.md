# Full Olist evidence gate (read-only)

**Status: procedure prepared; not executed against the user's full local dataset.**

The permanent GitHub CI uses a seven-order synthetic fixture. A passing CI run is not evidence of full Olist monetary totals, completeness, or cloud controls.

Run the gate from the repository root against an **existing** local DuckDB database with a built `main_marts.fct_olist_orders` table:

```powershell
python analytics/validate_full_olist.py --db "C:\path\to\existing\shopanalysis.duckdb" --compare-documented-controls
```

The example path is a placeholder; use the actual verified path. The script connects with `read_only=True`, returns only aggregate counts and amounts, and does not create files or query cloud services. It checks order-grain uniqueness, NULL order IDs, delivered partition completeness, NULL monetary values, order-level and aggregate monetary parity, and optionally compares delivered totals against the **historically documented** controls in `docs/metrics/revenue.md`. Comparison is opt-in to avoid misrepresenting a small fixture as a full-data validation.

**Documented historical controls, not measurements made by this update:** 96,478 delivered orders; merchandise 13,221,498.11; freight 2,198,275.64; gross 15,419,773.75; delivered payment 15,422,461.77; eight delivery-timestamp exceptions.

A PASS certifies only the checks performed against the specific database supplied. It does not certify input hashes, source row completeness, SCD2 chronology, refund/net revenue, payment-difference causes, RBAC, immutability, licensing, or deployment. Retain the run's timestamp, local DuckDB version, source manifest, dbt invocation and result, and exact database path in a **private** evidence log. Do not publish source rows or credentials.

Run the existing full-data dbt assertions separately, using the appropriate authorized full-data profile and target; the synthetic CI deliberately excludes those assertions. Do not use the synthetic target for full-data certification.

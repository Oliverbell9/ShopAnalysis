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

## RAW source-completeness check (separate from mart control)

Run the following **read-only** check against the existing full local database:

```powershell
python analytics/validate_raw_olist.py --db ".\\data\\shopanalysis.duckdb" --manifest ".\\data\\manifests\\olist_manifest.json"
```

The check compares the nine RAW table row counts against the recorded `data_rows` in the repository's Olist CSV manifest, checks four RAW lineage fields for NULLs, and requires one common non-NULL batch ID across all nine tables. This is **manifest-to-RAW cardinality and lineage-field evidence**, not a cryptographic source-integrity check. The script does **not** open or hash original CSV files, inspect upstream provider revisions, validate every source row's contents, or prove transformations from RAW to marts. The historical manifest is a reference; a matching count alone cannot prove data equivalence. Preserve output privately and investigate any mismatch rather than updating historical expectations to force a pass.

Synthetic CI tests the gate's pure validation rules; it does not run the full-data check.

## Original CSV integrity (separate, read-only check)

From the project root, after verifying that the **original** nine Olist CSV files exist under `data/raw/olist`, run:

```powershell
python analytics/validate_olist_csv_integrity.py --raw-root ".\\data\\raw\\olist" --manifest ".\\data\\manifests\\olist_manifest.json"
```

The script checks the exact nine-file inventory, byte sizes and SHA-256 fingerprints against the committed manifest. It streams the CSV bytes without rewriting files, exporting rows, or opening DuckDB. A PASS proves that the local files match the **recorded** fingerprints; it does not independently authenticate the manifest, original Kaggle acquisition, or upstream revisions. A missing local CSV is a failed/unavailable evidence check, **not** proof of data corruption. Never update the manifest merely to make a mismatch pass. Synthetic CI exercises isolated test files only.

## Selected RAW-to-mart order lineage (read-only)

After building the **full** Olist dbt models locally, run from the project root:

```powershell
python -m analytics.validate_olist_order_lineage --db ".\\data\\shopanalysis.duckdb"
```

This compares order-ID coverage and uniqueness from RAW orders through staging, enriched intermediate, reconciliation intermediate, and the order fact; verifies selected order fact monetary/status fields against intermediate outputs; and independently recomputes delivered monthly counts and money from the fact to compare with the monthly revenue mart. A mismatch is an evidence failure requiring investigation; it is not permission to change source records. The checker is read-only. It does **not** certify complete field-level lineage, other marts, acquisition authenticity, access controls or cloud deployment. Synthetic CI runs isolated Python assessment tests; the full dataset must be checked locally.

## Remaining Olist marts and dimensions (read-only)

From the project root, after building the full Olist dbt models:

```powershell
python -m analytics.validate_olist_remaining_marts --db ".\\data\\shopanalysis.duckdb"
```

This checks order-item composite keys and selected item fields, product/seller dimension keys, customer version/current-key consistency, and independently recomputes customer, seller and category delivered-revenue aggregates from the facts. Results are exceptions, with zero required for PASS. The checks are **bounded**: they do not certify all SCD2 intervals, all dimension attributes, complete field-level provenance, RBAC or cloud controls. Full Olist verification is local; synthetic CI only tests the Python assessment and guard.

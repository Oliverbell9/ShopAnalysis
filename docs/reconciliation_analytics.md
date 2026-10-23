# Revenue reconciliation and analytical scope

## Reproducible local control

The read-only tool `analytics/reconcile_revenue.py` checks the existing `main_marts.fct_olist_orders` order grain and delivered financial arithmetic without modifying the database or exporting data.

```powershell
python analytics/reconcile_revenue.py --db data/shopanalysis.duckdb
```

Replace the example path with the actual **existing** local DuckDB mart database; the script does not create one. Do not point it at a production database or a cloud endpoint. Unit tests for the pure calculation function are in `tests/test_reconcile_revenue.py`.

## Source-defined metrics

- Merchandise: sum of delivered-order item value.
- Freight: delivered-order freight value, separate from merchandise.
- Gross order value: delivered merchandise plus freight.
- Payment value: reconciliation evidence, **not** a substitute for gross order value.
- Net revenue, refunds, financing charges, and CAC: **not derivable** without additional authoritative source evidence.
- Purchase date and delivery date: distinct business clocks; do not substitute one for the other.

The original charter's Finance $4.8M / Marketing $5.1M / Operations $4.6M discrepancy is an **illustrative business scenario**, not a verified Olist source-system reconciliation. Do not report a 0.1% reconciliation result for those three values without corresponding source records and documented definitions.

## Evidence and limitations

The documented Olist delivered-order control totals in `docs/metrics/revenue.md` are dataset-specific and must be independently verified against a full Olist build. The synthetic CI fixture contains only seven orders and cannot validate those full-dataset totals.

This batch does not establish marketing attribution, refund/net revenue, retention modeling, cost benchmarks, or a validated forecasting/prediction model. Those require additional inputs and validation. No dashboard publication is authorized.

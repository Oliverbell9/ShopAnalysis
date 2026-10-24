"""Read-only order-key and delivered monthly lineage controls for full Olist DuckDB.

Validates selected transformation outputs, not complete column-level provenance.
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

LAYERS = (
    "raw.olist_orders",
    "main_staging.stg_olist__orders",
    "main_intermediate.int_olist__orders_enriched",
    "main_intermediate.int_olist__order_reconciliation",
    "main_marts.fct_olist_orders",
)


def assess(metrics):
    issues = []
    for key, value in metrics.items():
        if value:
            issues.append(f"{key}: {value} mismatched rows/keys")
    return issues


def inspect(path):
    if not path.is_file():
        raise FileNotFoundError(f"Existing DuckDB database required: {path}")
    import duckdb
    con = duckdb.connect(str(path.resolve()), read_only=True)
    metrics = {}
    try:
        for layer in LAYERS:
            metrics[f"{layer}.null_keys"] = con.execute(
                f"select count(*) from {layer} where order_id is null"
            ).fetchone()[0]
            metrics[f"{layer}.duplicate_keys"] = con.execute(
                f"select count(*) - count(distinct order_id) from {layer}"
            ).fetchone()[0]
        for left, right in itertools.pairwise(LAYERS):
            metrics[f"{left}-> {right}.missing"] = con.execute(
                f"select count(*) from {left} l where not exists "
                f"(select 1 from {right} r where r.order_id = l.order_id)"
            ).fetchone()[0]
            metrics[f"{right}-> {left}.unexpected"] = con.execute(
                f"select count(*) from {right} r where not exists "
                f"(select 1 from {left} l where l.order_id = r.order_id)"
            ).fetchone()[0]
        metrics["enriched_to_fact.order_status_mismatch"] = con.execute("""
            select count(*)
            from main_intermediate.int_olist__orders_enriched e
            join main_marts.fct_olist_orders f using (order_id)
            where e.order_status is distinct from f.order_status
               or e.customer_id is distinct from f.customer_id
               or e.item_revenue is distinct from f.merchandise_value
               or e.freight_revenue is distinct from f.freight_value
               or e.item_plus_freight is distinct from f.gross_order_value
               or e.payment_value is distinct from f.payment_value
        """).fetchone()[0]
        metrics["reconciliation_to_fact.status_mismatch"] = con.execute("""
            select count(*)
            from main_intermediate.int_olist__order_reconciliation r
            join main_marts.fct_olist_orders f using (order_id)
            where r.reconciliation_status is distinct from f.reconciliation_status
               or r.payment_item_difference is distinct from f.payment_item_difference
        """).fetchone()[0]
        metrics["monthly_mart.mismatched_months"] = con.execute("""
            with expected as (
                select cast(date_trunc('month', order_purchased_at) as date) purchase_month,
                    count(*) delivered_orders,
                    sum(merchandise_value) gross_merchandise_revenue,
                    sum(freight_value) freight_value,
                    sum(gross_order_value) gross_order_value
                from main_marts.fct_olist_orders
                where order_status = 'delivered'
                group by 1
            )
            select count(*)
            from expected e full outer join main_marts.mart_olist_monthly_revenue m
              using (purchase_month)
            where e.purchase_month is null or m.purchase_month is null
               or e.delivered_orders is distinct from m.delivered_orders
               or e.gross_merchandise_revenue is distinct from m.gross_merchandise_revenue
               or e.freight_value is distinct from m.freight_value
               or e.gross_order_value is distinct from m.gross_order_value
        """).fetchone()[0]
        return metrics
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    metrics = inspect(args.db)
    issues = assess(metrics)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    for issue in issues:
        print(f"FAIL: {issue}")
    if issues:
        raise SystemExit(1)
    print("PASS: selected order-key, fact-field and monthly aggregation lineage controls")
    print("NOT CERTIFIED: complete transformation provenance, other marts, RBAC, cloud controls")


if __name__ == "__main__":
    main()

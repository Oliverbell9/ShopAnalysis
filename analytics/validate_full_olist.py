"""Read-only full-Olist mart controls. No writes, cloud access or row-level exports."""
from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

DOCUMENTED_CONTROLS = {
    "delivered_orders": 96478,
    "merchandise": Decimal("13221498.11"),
    "freight": Decimal("2198275.64"),
    "gross": Decimal("15419773.75"),
    "payment": Decimal("15422461.77"),
    "delivery_timestamp_exceptions": 8,
}


def decimal_value(value):
    if value is None:
        raise ValueError("Missing aggregate monetary value")
    if isinstance(value, float):
        raise ValueError("Unexpected floating-point monetary aggregate")
    return Decimal(str(value))


def assess(metrics, *, compare_documented=False):
    """Pure assessment; comparison to historical controls must be explicitly requested."""
    issues = []
    if metrics["total_orders"] != metrics["distinct_order_ids"]:
        issues.append("Order-grain duplicate or NULL order IDs")
    if metrics["null_order_ids"]:
        issues.append("NULL order IDs")
    if metrics["delivered_orders"] + metrics["non_delivered_orders"] != metrics["total_orders"]:
        issues.append("Delivered status partition does not cover all orders")
    if metrics["delivered_null_money"]:
        issues.append("Delivered required merchandise, freight or gross values contain NULLs")
    if metrics["unclassified_missing_payments"]:
        issues.append("Delivered missing payments without missing_payment classification")
    if metrics["inconsistent_missing_payment_status"]:
        issues.append("Delivered missing_payment status has non-NULL payment or payment counts")
    if metrics["delivered_row_mismatches"]:
        issues.append("Delivered order-level merchandise + freight != gross")
    if metrics["merchandise"] + metrics["freight"] != metrics["gross"]:
        issues.append("Delivered aggregate merchandise + freight != gross")
    if compare_documented:
        for key, expected in DOCUMENTED_CONTROLS.items():
            if metrics[key] != expected:
                issues.append(f"Documented full-Olist control differs: {key}")
    return issues


def inspect(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Existing DuckDB database required: {path}")
    import duckdb
    con = duckdb.connect(str(path.resolve()), read_only=True)
    try:
        row = con.execute("""
            SELECT
                count(*) AS total_orders,
                count(DISTINCT order_id) AS distinct_order_ids,
                count(*) FILTER (WHERE order_id IS NULL) AS null_order_ids,
                count(*) FILTER (WHERE is_delivered IS TRUE) AS delivered_orders,
                count(*) FILTER (WHERE is_delivered IS NOT TRUE) AS non_delivered_orders,
                count(*) FILTER (
                    WHERE is_delivered IS TRUE AND
                    (merchandise_value IS NULL OR freight_value IS NULL
                     OR gross_order_value IS NULL)
                ) AS delivered_null_money,
                count(*) FILTER (
                    WHERE is_delivered IS TRUE AND payment_value IS NULL
                      AND (reconciliation_status IS DISTINCT FROM 'missing_payment'
                           OR payment_record_count IS NOT NULL
                           OR payment_type_count IS NOT NULL)
                ) AS unclassified_missing_payments,
                count(*) FILTER (
                    WHERE is_delivered IS TRUE
                      AND reconciliation_status = 'missing_payment'
                      AND (payment_value IS NOT NULL
                           OR payment_record_count IS NOT NULL
                           OR payment_type_count IS NOT NULL)
                ) AS inconsistent_missing_payment_status,
                count(*) FILTER (
                    WHERE is_delivered IS TRUE
                      AND payment_value IS NULL
                      AND reconciliation_status = 'missing_payment'
                      AND payment_record_count IS NULL
                      AND payment_type_count IS NULL
                ) AS classified_missing_payments,
                count(*) FILTER (
                    WHERE is_delivered IS TRUE AND
                    (merchandise_value + freight_value != gross_order_value)
                ) AS delivered_row_mismatches,
                sum(merchandise_value) FILTER (WHERE is_delivered IS TRUE) AS merchandise,
                sum(freight_value) FILTER (WHERE is_delivered IS TRUE) AS freight,
                sum(gross_order_value) FILTER (WHERE is_delivered IS TRUE) AS gross,
                sum(payment_value) FILTER (WHERE is_delivered IS TRUE) AS payment,
                count(*) FILTER (
                    WHERE is_delivered IS TRUE
                    AND is_delivery_timestamp_exception IS TRUE
                ) AS delivery_timestamp_exceptions
            FROM main_marts.fct_olist_orders
        """)
        keys = [column[0] for column in row.description]
        values = row.fetchone()
        if values is None or values[0] == 0:
            raise ValueError("Mart is empty; cannot certify full Olist")
        metrics = dict(zip(keys, values))
        for key in ("merchandise", "freight", "gross", "payment"):
            metrics[key] = decimal_value(metrics[key])
        return metrics
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--compare-documented-controls", action="store_true",
                        help="Compare actual results with historically documented Olist totals")
    args = parser.parse_args()
    metrics = inspect(args.db)
    issues = assess(metrics, compare_documented=args.compare_documented_controls)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    if issues:
        for issue in issues:
            print(f"FAIL: {issue}")
        raise SystemExit(1)
    print("PASS: selected order-grain and monetary controls")
    if not args.compare_documented_controls:
        print("NOT CERTIFIED: historical full-Olist totals were not compared")
    else:
        print("PASS: historical documented control totals match")
    print("NOT CERTIFIED: source completeness, permissions, lineage and cloud controls")


if __name__ == "__main__":
    main()

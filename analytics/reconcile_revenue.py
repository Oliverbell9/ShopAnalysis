"""Read-only governed revenue reconciliation report; no data export by default.

Input is an existing local DuckDB mart database. Never connects to cloud services.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

MONEY = ("merchandise_value", "freight_value", "gross_order_value")


def as_money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, float):
        raise ValueError("Floating-point money is not accepted")  # noqa: TRY004 - monetary validation contract
    return Decimal(str(value))


def summarize_rows(rows):
    """Pure function for synthetic unit testing; one row per order."""
    order_ids = [row["order_id"] for row in rows]
    if len(order_ids) != len(set(order_ids)):
        raise ValueError("Duplicate order_id violates order-grain contract")
    delivered = [r for r in rows if r["is_delivered"] is True]
    totals = {key: sum((as_money(r[key]) for r in delivered), Decimal("0.00"))
              for key in MONEY}
    if totals["merchandise_value"] + totals["freight_value"] != totals["gross_order_value"]:
        raise ValueError("Delivered merchandise + freight != gross")
    counts = {}
    for row in rows:
        status = row["reconciliation_status"]
        counts[status] = counts.get(status, 0) + 1
    return {
        "total_orders": len(rows),
        "delivered_orders": len(delivered),
        "totals": totals,
        "reconciliation_status_counts": dict(sorted(counts.items())),
        "delivery_timestamp_exceptions": sum(
            1 for r in delivered if r["is_delivery_timestamp_exception"] is True
        ),
    }


def inspect_database(path: Path):
    if not path.is_file():
        raise FileNotFoundError(path)
    import duckdb
    con = duckdb.connect(str(path.resolve()), read_only=True)
    try:
        cursor = con.execute(
            """SELECT order_id, is_delivered, merchandise_value,
                      freight_value, gross_order_value,
                      reconciliation_status, is_delivery_timestamp_exception
               FROM main_marts.fct_olist_orders"""
        )
        names = [item[0] for item in cursor.description]
        return summarize_rows([dict(zip(names, row)) for row in cursor.fetchall()])
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    result = inspect_database(args.db)
    for key in ("total_orders", "delivered_orders", "delivery_timestamp_exceptions"):
        print(f"{key}: {result[key]}")
    for key, value in result["totals"].items():
        print(f"{key}: {value}")
    for status, count in result["reconciliation_status_counts"].items():
        print(f"reconciliation.{status}: {count}")
    print("PASS: order-grain and delivered monetary parity checks")


if __name__ == "__main__":
    main()

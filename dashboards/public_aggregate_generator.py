"""ShopAnalysis public aggregate builder. Read-only, in-memory; never exports files.

Proposed revenue measures use source monetary units, delivered purchase cohorts,
not net revenue. Run `python public_aggregate_generator.py --db PATH --validate-only`.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

MONEY = ("merchandise", "freight", "gross")
EXPECTED = {"executive_kpis": 1, "revenue_periods": 21,
            "customer_states": 27, "product_categories": 72,
            "payment_reconciliation": 5, "repeat_customers": 2}
EXPECTED_MONEY = (Decimal("13221498.11"), Decimal("2198275.64"), Decimal("15419773.75"))
ALLOWED = {
    "executive_kpis": ("delivered_orders", *MONEY),
    "revenue_periods": ("reporting_period", "delivered_orders", *MONEY),
    "customer_states": ("customer_state", "delivered_orders", *MONEY),
    "product_categories": ("public_category", "distinct_delivered_orders", *MONEY),
    "payment_reconciliation": ("public_status", "orders"),
    "repeat_customers": ("is_repeat_customer", "customers", "gross_order_value"),
}
QUERIES = {
    "executive_kpis": """SELECT COUNT(*) AS delivered_orders,
        SUM(merchandise_value) AS merchandise, SUM(freight_value) AS freight,
        SUM(gross_order_value) AS gross
        FROM main_marts.fct_olist_orders WHERE is_delivered = TRUE""",
    "revenue_periods": """SELECT CASE WHEN order_purchased_at >= TIMESTAMP '2016-09-01'
        AND order_purchased_at < TIMESTAMP '2017-01-01' THEN '2016 launch period'
        ELSE STRFTIME(order_purchased_at, '%Y-%m') END AS reporting_period,
        COUNT(*) AS delivered_orders, SUM(merchandise_value) AS merchandise,
        SUM(freight_value) AS freight, SUM(gross_order_value) AS gross
        FROM main_marts.fct_olist_orders WHERE is_delivered = TRUE
        GROUP BY 1 ORDER BY 1""",
    "customer_states": """SELECT customer_state, COUNT(*) AS delivered_orders,
        SUM(merchandise_value) AS merchandise, SUM(freight_value) AS freight,
        SUM(gross_order_value) AS gross
        FROM main_marts.fct_olist_orders WHERE is_delivered = TRUE
        GROUP BY 1 ORDER BY 1""",
    "product_categories": """WITH low_volume AS (
        SELECT product_category_name FROM main_marts.mart_olist_category_revenue
        WHERE distinct_delivered_orders < 10
    ), classified AS (
        SELECT i.order_id,
          CASE WHEN EXISTS (SELECT 1 FROM low_volume l WHERE
            p.product_category_name IS NOT DISTINCT FROM l.product_category_name)
            THEN 'Other low-volume categories'
            ELSE COALESCE(p.product_category_name, 'Uncategorized') END AS public_category,
          i.merchandise_value, i.freight_value, i.item_gross_value
        FROM main_marts.fct_olist_order_items i
        JOIN main_marts.dim_product p ON i.product_id = p.product_id
        WHERE i.is_delivered = TRUE
    ) SELECT public_category, COUNT(DISTINCT order_id) AS distinct_delivered_orders,
        SUM(merchandise_value) AS merchandise, SUM(freight_value) AS freight,
        SUM(item_gross_value) AS gross FROM classified GROUP BY 1 ORDER BY 1""",
    "payment_reconciliation": """SELECT CASE WHEN reconciliation_status IN
        ('missing_payment','missing_items') THEN 'missing_payment_or_item_records'
        ELSE COALESCE(reconciliation_status, 'unclassified') END AS public_status,
        COUNT(*) AS orders FROM main_marts.fct_olist_orders GROUP BY 1 ORDER BY 1""",
    "repeat_customers": """SELECT is_repeat_customer, COUNT(*) AS customers,
        SUM(gross_order_value) AS gross_order_value
        FROM main_marts.mart_olist_customer_revenue GROUP BY 1 ORDER BY 1""",
}


def as_decimal(value):
    if value is None or isinstance(value, float):
        raise ValueError("Missing or floating-point monetary value")
    return Decimal(str(value))


def validate(data):
    """Fail closed; no data is written. Checks are not a full privacy audit."""
    if set(data) != set(EXPECTED):
        raise ValueError("Unexpected dataset names")
    for name, rows in data.items():
        if len(rows) != EXPECTED[name]:
            raise ValueError(f"{name}: expected {EXPECTED[name]} rows, got {len(rows)}")
        if any(set(row) != set(ALLOWED[name]) for row in rows):
            raise ValueError(f"{name}: unexpected or missing column")
        for row in rows:
            for key in row:
                if row[key] is None:
                    raise ValueError(f"{name}: NULL value in {key}")
            if all(k in row for k in MONEY):
                m, f, g = (as_decimal(row[k]) for k in MONEY)
                if m + f != g:
                    raise ValueError(f"{name}: financial reconciliation failure")
    group_keys = {
        "revenue_periods": "reporting_period",
        "customer_states": "customer_state",
        "product_categories": "public_category",
        "payment_reconciliation": "public_status",
        "repeat_customers": "is_repeat_customer",
    }
    for dataset, key in group_keys.items():
        values = [row[key] for row in data[dataset]]
        try:
            unique_count = len(set(values))
        except TypeError as exc:
            raise ValueError(
                f"{dataset}: unhashable grouping key"
            ) from exc
        if unique_count != len(values):
            raise ValueError(
                f"{dataset}: duplicate grouping keys"
            )
    kpi = data["executive_kpis"][0]
    if kpi["delivered_orders"] != 96478 or tuple(as_decimal(kpi[k]) for k in MONEY) != EXPECTED_MONEY:
        raise ValueError("Unexpected executive KPI totals")
    for name in ("revenue_periods", "customer_states", "product_categories"):
        rows = data[name]
        if tuple(sum((as_decimal(r[k]) for r in rows), Decimal("0")) for k in MONEY) != EXPECTED_MONEY:
            raise ValueError(f"{name}: monetary parity failed")
    for name in ("revenue_periods", "customer_states"):
        rows = data[name]
        if sum(r["delivered_orders"] for r in rows) != 96478:
            raise ValueError(f"{name}: delivered-order parity failed")
        if min(r["delivered_orders"] for r in rows) < 10:
            raise ValueError(f"{name}: small group")
    if min(r["distinct_delivered_orders"] for r in data["product_categories"]) < 10:
        raise ValueError("product_categories: small group")
    if len({r["public_category"] for r in data["product_categories"]}) != 72:
        raise ValueError("product_categories: duplicate labels")
    periods = {r["reporting_period"] for r in data["revenue_periods"]}
    expected_periods = {"2016 launch period"} | {f"{year}-{month:02d}" for year, months in ((2017, range(1, 13)), (2018, range(1, 9))) for month in months}
    if periods != expected_periods:
        raise ValueError("Unexpected reporting periods")
    payments = {r["public_status"]: r["orders"] for r in data["payment_reconciliation"]}
    if payments != {"exact_match": 98089, "missing_payment_or_item_records": 776,
                    "within_one_cent": 273, "payment_above_item_plus_freight": 264,
                    "payment_below_item_plus_freight": 39}:
        raise ValueError("Payment classification mismatch")
    repeat = {r["is_repeat_customer"]: r for r in data["repeat_customers"]}
    if set(repeat) != {False, True} or repeat[False]["customers"] != 90557 or repeat[True]["customers"] != 2801:
        raise ValueError("Repeat-customer counts mismatch")
    if sum((as_decimal(r["gross_order_value"]) for r in repeat.values()), Decimal("0")) != EXPECTED_MONEY[2]:
        raise ValueError("Repeat-customer gross parity failed")
    if min(r["customers"] for r in repeat.values()) < 10:
        raise ValueError("Repeat-customer small group")
    return True


def build_in_memory(db_path: Path):
    """Read a local DuckDB database without changing it or writing exports."""
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    import duckdb
    con = duckdb.connect(str(db_path.resolve()), read_only=True)
    try:
        result = {}
        for name, sql in QUERIES.items():
            cursor = con.execute(sql)
            columns = [column[0] for column in cursor.description]
            if set(columns) != set(ALLOWED[name]):
                raise ValueError(f"{name}: unexpected query schema")
            result[name] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        validate(result)
        return result
    finally:
        con.close()



def export_csv(data, output_dir: Path):
    """Export validated aggregates to a new directory; never overwrite."""
    import csv

    validate(data)
    output_dir = Path(output_dir)

    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(
            f"Export destination already exists: {output_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=False)
    created_files = []

    try:
        for name in EXPECTED:
            path = output_dir / f"{name}.csv"
            columns = ALLOWED[name]

            with path.open("x", newline="", encoding="utf-8") as handle:
                created_files.append(path)
                writer = csv.DictWriter(
                    handle,
                    fieldnames=columns,
                    extrasaction="raise",
                )
                writer.writeheader()
                writer.writerows(data[name])

            with path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)

                if reader.fieldnames != list(columns):
                    raise ValueError(f"{name}: exported header mismatch")

                actual = list(reader)

            expected = [
                {key: str(row[key]) for key in columns}
                for row in data[name]
            ]

            if actual != expected:
                raise ValueError(
                    f"{name}: exported content mismatch"
                )

        actual_files = {
            path.name for path in output_dir.iterdir()
            if path.is_file()
        }
        expected_files = {
            f"{name}.csv" for name in EXPECTED
        }

        if actual_files != expected_files:
            raise ValueError("Unexpected exported file inventory")

    except Exception:
        for created_file in reversed(created_files):
            if created_file.is_file() and not created_file.is_symlink():
                created_file.unlink()

        try:
            output_dir.rmdir()
        except OSError:
            pass

        raise

    return tuple(output_dir / f"{name}.csv" for name in EXPECTED)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--validate-only", action="store_true", required=True,
                        help="Required safety flag: never export any files")
    args = parser.parse_args()
    data = build_in_memory(args.db)
    for name in EXPECTED:
        print(f"{name}: {len(data[name])} groups — PASS")
    print("READ-ONLY VALIDATION PASS; NO FILES EXPORTED")


if __name__ == "__main__":
    main()

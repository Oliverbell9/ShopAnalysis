"""Read-only comparison of nine RAW Olist tables to the documented CSV manifest.

Row counts and RAW lineage are checked; original CSV hashes are NOT verified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ENTITY_TABLES = {
    "olist_customers_dataset.csv": "olist_customers",
    "olist_geolocation_dataset.csv": "olist_geolocation",
    "olist_order_items_dataset.csv": "olist_order_items",
    "olist_order_payments_dataset.csv": "olist_payments",
    "olist_order_reviews_dataset.csv": "olist_reviews",
    "olist_orders_dataset.csv": "olist_orders",
    "olist_products_dataset.csv": "olist_products",
    "olist_sellers_dataset.csv": "olist_sellers",
    "product_category_name_translation.csv": "olist_translation",
}
LINEAGE_COLUMNS = ("_source_file", "_file_row_number", "_loaded_at", "_batch_id")


def expected_rows(manifest):
    files = manifest["files"]
    names = [item["file_name"] for item in files]
    if len(names) != len(ENTITY_TABLES) or set(names) != set(ENTITY_TABLES):
        raise ValueError("Manifest must contain exactly the nine expected Olist CSV files")
    if len(names) != len(set(names)):
        raise ValueError("Duplicate source filename in manifest")
    counts = {}
    for item in files:
        value = item["data_rows"]
        if type(value) is not int or value <= 0:
            raise ValueError(f"Invalid manifest data_rows: {item['file_name']}")
        counts[ENTITY_TABLES[item["file_name"]]] = value
    return counts


def assess(results):
    issues = []
    batches = set()
    for table, record in results.items():
        if record["actual"] != record["expected"]:
            issues.append(f"{table}: RAW row count differs from manifest")
        if record["null_lineage"]:
            issues.append(f"{table}: NULL lineage fields")
        if record["distinct_batches"] != 1 or record["batch_id"] is None:
            issues.append(f"{table}: expected one non-NULL batch ID")
        else:
            batches.add(record["batch_id"])
    if len(batches) > 1:
        issues.append("RAW tables contain different batch IDs")
    return issues


def inspect(db_path, manifest_path):
    if not db_path.is_file():
        raise FileNotFoundError(f"Existing DuckDB required: {db_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = expected_rows(manifest)
    import duckdb
    con = duckdb.connect(str(db_path.resolve()), read_only=True)
    results = {}
    try:
        for table, count in expected.items():
            # Table identifiers are exclusively from the fixed ENTITY_TABLES map.
            row = con.execute(f"""
                SELECT COUNT(*),
                    COUNT(*) FILTER (WHERE
                        _source_file IS NULL OR _file_row_number IS NULL
                        OR _loaded_at IS NULL OR _batch_id IS NULL),
                    COUNT(DISTINCT _batch_id), MIN(_batch_id)
                FROM raw.{table}
            """).fetchone()
            results[table] = {
                "expected": count,
                "actual": row[0],
                "null_lineage": row[1],
                "distinct_batches": row[2],
                "batch_id": row[3],
            }
    finally:
        con.close()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path,
                        default=Path("data/manifests/olist_manifest.json"))
    args = parser.parse_args()
    results = inspect(args.db, args.manifest)
    for table, item in results.items():
        print(f"{table}: manifest={item['expected']} raw={item['actual']} "
              f"null_lineage={item['null_lineage']} "
              f"batch_count={item['distinct_batches']}")
    issues = assess(results)
    for issue in issues:
        print(f"FAIL: {issue}")
    if issues:
        raise SystemExit(1)
    print("PASS: nine RAW table counts and lineage/batch checks")
    print("NOT CERTIFIED: CSV file hashes, acquisition authenticity, "
          "transformation lineage, RBAC, or cloud controls")


if __name__ == "__main__":
    main()

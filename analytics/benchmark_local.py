"""Read-only local DuckDB query benchmark; no cloud cost claims or exports."""
from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

QUERIES = {
    "delivered_kpis": """
        SELECT COUNT(*) AS orders,
               SUM(merchandise_value) AS merchandise,
               SUM(freight_value) AS freight,
               SUM(gross_order_value) AS gross
        FROM main_marts.fct_olist_orders
        WHERE is_delivered = TRUE
    """,
    "monthly_mart": """
        SELECT COUNT(*) AS months, SUM(delivered_orders) AS orders,
               SUM(gross_order_value) AS gross
        FROM main_marts.mart_olist_monthly_revenue
    """,
}


def measure(connection, query: str, repetitions: int):
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    # Warm-up separately; do not represent warm-up as a measured run.
    connection.execute(query).fetchall()
    samples = []
    results = []
    for _ in range(repetitions):
        start = time.perf_counter()
        result = connection.execute(query).fetchall()
        samples.append((time.perf_counter() - start) * 1000)
        results.append(result)
    if any(result != results[0] for result in results[1:]):
        raise RuntimeError("Nonrepeatable query results")
    return {
        "repetitions": repetitions,
        "min_ms": min(samples),
        "median_ms": statistics.median(samples),
        "max_ms": max(samples),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if args.repetitions < 1 or args.repetitions > 100:
        parser.error("--repetitions must be between 1 and 100")
    if not args.db.is_file():
        parser.error("Existing DuckDB database required; refusing to create one")
    import duckdb
    connection = duckdb.connect(str(args.db.resolve()), read_only=True)
    try:
        for name, query in QUERIES.items():
            result = measure(connection, query, args.repetitions)
            print(f"{name}: repetitions={result['repetitions']} "
                  f"min_ms={result['min_ms']:.3f} "
                  f"median_ms={result['median_ms']:.3f} "
                  f"max_ms={result['max_ms']:.3f}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()

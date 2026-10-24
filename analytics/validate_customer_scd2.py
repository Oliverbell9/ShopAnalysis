"""Read-only customer SCD2 effective dating and historical assignment checks."""
from __future__ import annotations

import argparse
from pathlib import Path

QUERIES = {
    "dimension.null_required_fields": """
        select count(*) from main_marts.dim_customer
        where customer_unique_id is null or customer_sk is null
           or customer_version is null or valid_from is null or is_current is null
    """,
    "dimension.duplicate_surrogate_keys": """
        select count(*) - count(distinct customer_sk) from main_marts.dim_customer
    """,
    "dimension.nonpositive_versions": """
        select count(*) from main_marts.dim_customer where customer_version < 1
    """,
    "dimension.invalid_intervals": """
        select count(*) from main_marts.dim_customer
        where valid_to is not null and valid_to <= valid_from
    """,
    "dimension.nonsequential_versions": """
        select count(*) from (
          select customer_version,
            row_number() over(partition by customer_unique_id order by customer_version) expected_version
          from main_marts.dim_customer
        ) where customer_version != expected_version
    """,
    "dimension.interval_adjacency_mismatches": """
        with sequenced as (
          select valid_to,
            lead(valid_from) over(partition by customer_unique_id order by customer_version) next_from
          from main_marts.dim_customer
        )
        select count(*) from sequenced
        where next_from is not null and valid_to is distinct from next_from
    """,
    "dimension.current_flag_mismatches": """
        select count(*) from main_marts.dim_customer
        where is_current is distinct from (valid_to is null)
    """,
    "dimension.surrogate_key_mismatches": """
        select count(*) from main_marts.dim_customer
        where customer_sk is distinct from md5(customer_unique_id || '|' || cast(customer_version as varchar))
    """,
    "dimension.version_order_count_mismatches": """
        select count(*) from main_marts.dim_customer d
        left join (
          select d2.customer_sk, count(*) order_count
          from main_intermediate.int_olist__orders_enriched o
          join main_marts.dim_customer d2
            on o.customer_unique_id=d2.customer_unique_id
           and o.order_purchased_at >= d2.valid_from
           and (o.order_purchased_at < d2.valid_to or d2.valid_to is null)
          group by 1
        ) a on d.customer_sk=a.customer_sk
        where d.orders_in_version is distinct from coalesce(a.order_count, 0)
    """,
    "fact.missing_or_multiple_historical_matches": """
        select count(*) from (
          select o.order_id, count(d.customer_sk) match_count
          from main_intermediate.int_olist__orders_enriched o
          left join main_marts.dim_customer d
            on o.customer_unique_id=d.customer_unique_id
           and o.order_purchased_at >= d.valid_from
           and (o.order_purchased_at < d.valid_to or d.valid_to is null)
          group by 1
        ) where match_count != 1
    """,
    "fact.incorrect_customer_sk": """
        select count(*) from main_marts.fct_olist_orders f
        join main_marts.dim_customer d
          on f.customer_unique_id=d.customer_unique_id
         and f.order_purchased_at >= d.valid_from
         and (f.order_purchased_at < d.valid_to or d.valid_to is null)
        where f.customer_sk is distinct from d.customer_sk
    """,
    "fact.customer_sk_missing_dimension": """
        select count(*) from main_marts.fct_olist_orders f
        where not exists (
          select 1 from main_marts.dim_customer d where d.customer_sk=f.customer_sk
        )
    """,
}


def assess(metrics):
    return [f"{key}: {value} exceptions" for key, value in metrics.items() if value != 0]


def inspect(path):
    if not path.is_file():
        raise FileNotFoundError(f"Existing DuckDB database required: {path}")
    import duckdb
    con = duckdb.connect(str(path.resolve()), read_only=True)
    try:
        return {key: con.execute(sql).fetchone()[0] for key, sql in QUERIES.items()}
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
    print("PASS: selected customer SCD2 interval and historical assignment controls")
    print("NOT CERTIFIED: independent source provenance, full attribute-change history, RBAC or cloud controls")


if __name__ == "__main__":
    main()

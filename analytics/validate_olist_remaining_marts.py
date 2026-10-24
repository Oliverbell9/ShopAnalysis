"""Read-only selected grain, relationship and revenue rollup checks for Olist marts.

These checks do not establish full transformation provenance or cloud security.
"""
from __future__ import annotations

import argparse
from pathlib import Path

QUERIES = {
    "order_items.duplicate_keys": """
        select count(*) - count(distinct (order_id, order_item_id))
        from main_marts.fct_olist_order_items
    """,
    "order_items.missing_from_staging": """
        select count(*) from main_staging.stg_olist__order_items s
        where not exists (
            select 1 from main_marts.fct_olist_order_items f
            where f.order_id=s.order_id and f.order_item_id=s.order_item_id)
    """,
    "order_items.unexpected_in_fact": """
        select count(*) from main_marts.fct_olist_order_items f
        where not exists (
            select 1 from main_staging.stg_olist__order_items s
            where f.order_id=s.order_id and f.order_item_id=s.order_item_id)
    """,
    "order_items.field_mismatches": """
        select count(*) from main_marts.fct_olist_order_items f
        join main_staging.stg_olist__order_items s
          on f.order_id=s.order_id and f.order_item_id=s.order_item_id
        join main_marts.fct_olist_orders o on f.order_id=o.order_id
        where f.product_id is distinct from s.product_id
           or f.seller_id is distinct from s.seller_id
           or f.merchandise_value is distinct from s.price
           or f.freight_value is distinct from s.freight_value
           or f.item_gross_value is distinct from s.price+s.freight_value
           or f.is_delivered is distinct from o.is_delivered
    """,
    "product_dimension.duplicate_keys": """
        select count(*) - count(distinct product_id) from main_marts.dim_product
    """,
    "product_dimension.missing_or_unexpected_keys": """
        select count(*) from (
            (select product_id from main_staging.stg_olist__products
             except select product_id from main_marts.dim_product)
            union all
            (select product_id from main_marts.dim_product
             except select product_id from main_staging.stg_olist__products)
        )
    """,
    "seller_dimension.duplicate_keys": """
        select count(*) - count(distinct seller_id) from main_marts.dim_seller
    """,
    "seller_dimension.missing_or_unexpected_keys": """
        select count(*) from (
            (select seller_id from main_staging.stg_olist__sellers
             except select seller_id from main_marts.dim_seller)
            union all
            (select seller_id from main_marts.dim_seller
             except select seller_id from main_staging.stg_olist__sellers)
        )
    """,
    "customer_dimension.duplicate_versions": """
        select count(*) - count(distinct (customer_unique_id, customer_version))
        from main_marts.dim_customer
    """,
    "customer_dimension.current_version_exceptions": """
        select count(*) from (
            select customer_unique_id
            from main_marts.dim_customer
            group by 1
            having count(*) filter (where is_current is true) != 1
        )
    """,
    "customer_dimension.missing_unique_ids": """
        select count(*) from (
            select distinct customer_unique_id
            from main_intermediate.int_olist__orders_enriched
            except
            select customer_unique_id from main_marts.dim_customer
        )
    """,
    "customer_revenue.mismatched_groups": """
        with expected as (
            select customer_unique_id, count(*) n,
                sum(merchandise_value) merchandise, sum(freight_value) freight,
                sum(gross_order_value) gross
            from main_marts.fct_olist_orders where is_delivered is true
            group by 1
        )
        select count(*) from expected e
        full outer join main_marts.mart_olist_customer_revenue m using(customer_unique_id)
        where e.customer_unique_id is null or m.customer_unique_id is null
           or e.n is distinct from m.delivered_orders
           or e.merchandise is distinct from m.gross_merchandise_revenue
           or e.freight is distinct from m.freight_value
           or e.gross is distinct from m.gross_order_value
    """,
    "seller_revenue.mismatched_groups": """
        with expected as (
            select seller_id, count(*) n, count(distinct order_id) orders,
                sum(merchandise_value) merchandise, sum(freight_value) freight,
                sum(item_gross_value) gross
            from main_marts.fct_olist_order_items where is_delivered is true
            group by 1
        )
        select count(*) from expected e
        full outer join main_marts.mart_olist_seller_revenue m using(seller_id)
        where e.seller_id is null or m.seller_id is null
           or e.n is distinct from m.delivered_item_rows
           or e.orders is distinct from m.distinct_delivered_orders
           or e.merchandise is distinct from m.gross_merchandise_revenue
           or e.freight is distinct from m.freight_value
           or e.gross is distinct from m.gross_order_value
    """,
    "category_revenue.mismatched_groups": """
        with expected as (
            select p.product_category_name, p.product_category_name_english,
                p.category_translation_status, count(*) n,
                count(distinct i.order_id) orders,
                sum(i.merchandise_value) merchandise,
                sum(i.freight_value) freight, sum(i.item_gross_value) gross
            from main_marts.fct_olist_order_items i
            join main_marts.dim_product p on i.product_id=p.product_id
            where i.is_delivered is true
            group by 1,2,3
        )
        select count(*) from expected e
        full outer join main_marts.mart_olist_category_revenue m
          on e.product_category_name is not distinct from m.product_category_name
         and e.product_category_name_english is not distinct from m.product_category_name_english
         and e.category_translation_status is not distinct from m.category_translation_status
        where e.n is null or m.delivered_item_rows is null
           or e.n is distinct from m.delivered_item_rows
           or e.orders is distinct from m.distinct_delivered_orders
           or e.merchandise is distinct from m.gross_merchandise_revenue
           or e.freight is distinct from m.freight_value
           or e.gross is distinct from m.gross_order_value
    """,
}


def assess(metrics):
    return [f"{name}: {value} exceptions" for name, value in metrics.items() if value != 0]


def inspect(path):
    if not path.is_file():
        raise FileNotFoundError(f"Existing DuckDB database required: {path}")
    import duckdb
    con = duckdb.connect(str(path.resolve()), read_only=True)
    try:
        return {name: con.execute(query).fetchone()[0] for name, query in QUERIES.items()}
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    metrics = inspect(args.db)
    issues = assess(metrics)
    for name, value in metrics.items():
        print(f"{name}: {value}")
    for issue in issues:
        print(f"FAIL: {issue}")
    if issues:
        raise SystemExit(1)
    print("PASS: selected remaining Olist mart and dimension controls")
    print("NOT CERTIFIED: full field-level lineage, all SCD2 intervals, RBAC or cloud controls")


if __name__ == "__main__":
    main()

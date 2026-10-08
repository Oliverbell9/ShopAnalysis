-- Expected result: zero rows.
-- Independently reconcile each category to delivered item records.

with expected as (

    select
        p.product_category_name,
        p.product_category_name_english,
        p.category_translation_status,
        count(*) as delivered_item_rows,
        count(distinct i.order_id) as distinct_delivered_orders,
        sum(i.merchandise_value) as gross_merchandise_revenue,
        sum(i.freight_value) as freight_value,
        sum(i.item_gross_value) as gross_order_value

    from {{ ref('fct_olist_order_items') }} i

    inner join {{ ref('dim_product') }} p
        on i.product_id = p.product_id

    where i.is_delivered = true

    group by 1, 2, 3

),

actual as (

    select *
    from {{ ref('mart_olist_category_revenue') }}

)

select
    coalesce(e.product_category_name, a.product_category_name)
        as product_category_name,
    'category_reconciliation_mismatch' as violation

from expected e

full outer join actual a
    on e.product_category_name
        is not distinct from a.product_category_name

where
    e.category_translation_status is null
    or a.category_translation_status is null
    or e.product_category_name_english
        is distinct from a.product_category_name_english
    or e.category_translation_status
        is distinct from a.category_translation_status
    or e.delivered_item_rows
        is distinct from a.delivered_item_rows
    or e.distinct_delivered_orders
        is distinct from a.distinct_delivered_orders
    or e.gross_merchandise_revenue
        is distinct from a.gross_merchandise_revenue
    or e.freight_value
        is distinct from a.freight_value
    or e.gross_order_value
        is distinct from a.gross_order_value

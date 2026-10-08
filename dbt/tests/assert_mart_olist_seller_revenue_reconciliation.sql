with expected as (

    select
        i.seller_id,
        count(*) as delivered_item_rows,
        count(distinct i.order_id) as distinct_delivered_orders,
        sum(i.merchandise_value) as gross_merchandise_revenue,
        sum(i.freight_value) as freight_value,
        sum(i.item_gross_value) as gross_order_value

    from {{ ref('fct_olist_order_items') }} i

    inner join {{ ref('dim_seller') }} s
        on i.seller_id = s.seller_id

    where i.is_delivered = true

    group by i.seller_id

),

actual as (

    select *
    from {{ ref('mart_olist_seller_revenue') }}

)

select
    coalesce(e.seller_id, a.seller_id) as seller_id,
    e.delivered_item_rows as expected_items,
    a.delivered_item_rows as actual_items,
    e.gross_order_value as expected_gross,
    a.gross_order_value as actual_gross

from expected e

full outer join actual a
    on e.seller_id = a.seller_id

where e.seller_id is null
   or a.seller_id is null
   or e.delivered_item_rows is distinct from a.delivered_item_rows
   or e.distinct_delivered_orders is distinct from a.distinct_delivered_orders
   or e.gross_merchandise_revenue is distinct from a.gross_merchandise_revenue
   or e.freight_value is distinct from a.freight_value
   or e.gross_order_value is distinct from a.gross_order_value

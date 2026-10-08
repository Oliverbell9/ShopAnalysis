with expected as (

    select
        customer_unique_id,
        count(*) as delivered_orders,
        min(order_purchased_at) as first_delivered_purchase_at,
        max(order_purchased_at) as last_delivered_purchase_at,
        sum(merchandise_value) as gross_merchandise_revenue,
        sum(freight_value) as freight_value,
        sum(gross_order_value) as gross_order_value

    from {{ ref('fct_olist_orders') }}

    where is_delivered = true

    group by customer_unique_id

),

actual as (

    select *
    from {{ ref('mart_olist_customer_revenue') }}

)

select
    coalesce(e.customer_unique_id, a.customer_unique_id)
        as customer_unique_id,
    e.delivered_orders as expected_orders,
    a.delivered_orders as actual_orders,
    e.gross_order_value as expected_gross,
    a.gross_order_value as actual_gross

from expected e

full outer join actual a
    on e.customer_unique_id = a.customer_unique_id

where e.customer_unique_id is null
   or a.customer_unique_id is null
   or e.delivered_orders is distinct from a.delivered_orders
   or e.first_delivered_purchase_at
        is distinct from a.first_delivered_purchase_at
   or e.last_delivered_purchase_at
        is distinct from a.last_delivered_purchase_at
   or e.gross_merchandise_revenue
        is distinct from a.gross_merchandise_revenue
   or e.freight_value is distinct from a.freight_value
   or e.gross_order_value is distinct from a.gross_order_value

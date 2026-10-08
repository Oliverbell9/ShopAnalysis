{{ config(materialized='table') }}

with order_items as (

    select *
    from {{ ref('stg_olist__order_items') }}

),

orders as (

    select
        order_id,
        order_purchased_at,
        order_status,
        is_delivered
    from {{ ref('fct_olist_orders') }}

),

final as (

    select
        i.order_id,
        i.order_item_id,

        i.product_id,
        i.seller_id,

        o.order_purchased_at,
        o.order_status,
        o.is_delivered,

        i.shipping_limit_at,

        i.price as merchandise_value,
        i.freight_value,
        i.price + i.freight_value as item_gross_value

    from order_items i

    inner join orders o
        on i.order_id = o.order_id

)

select *
from final

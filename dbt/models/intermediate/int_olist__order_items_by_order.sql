with order_items as (

    select *
    from {{ ref('stg_olist__order_items') }}

),

aggregated as (

    select
        order_id,

        count(*) as item_count,
        count(distinct product_id) as distinct_product_count,
        count(distinct seller_id) as distinct_seller_count,

        sum(price) as item_revenue,
        sum(freight_value) as freight_revenue,
        sum(price + freight_value) as item_plus_freight,

        min(shipping_limit_at) as first_shipping_limit_at,
        max(shipping_limit_at) as last_shipping_limit_at

    from order_items
    group by order_id

)

select *
from aggregated

{{ config(materialized='table') }}

with delivered_orders as (

    select
        order_id,
        customer_unique_id,
        order_purchased_at,
        merchandise_value,
        freight_value,
        gross_order_value

    from {{ ref('fct_olist_orders') }}

    where is_delivered = true

),

customer_revenue as (

    select
        customer_unique_id,

        count(*) as delivered_orders,

        min(order_purchased_at) as first_delivered_purchase_at,

        max(order_purchased_at) as last_delivered_purchase_at,

        sum(merchandise_value) as gross_merchandise_revenue,

        sum(freight_value) as freight_value,

        sum(gross_order_value) as gross_order_value

    from delivered_orders

    group by customer_unique_id

),

current_customers as (

    select
        customer_unique_id,
        customer_city,
        customer_state,
        customer_zip_code_prefix

    from {{ ref('dim_customer') }}

    where is_current = true

),

final as (

    select
        r.customer_unique_id,

        c.customer_city,
        c.customer_state,
        c.customer_zip_code_prefix,

        r.delivered_orders,

        case
            when r.delivered_orders > 1 then true
            else false
        end as is_repeat_customer,

        r.first_delivered_purchase_at,
        r.last_delivered_purchase_at,

        date_diff(
            'day',
            r.first_delivered_purchase_at,
            r.last_delivered_purchase_at
        ) as purchase_span_days,

        r.gross_merchandise_revenue,
        r.freight_value,
        r.gross_order_value,

        r.gross_order_value / nullif(r.delivered_orders, 0)
            as average_gross_order_value

    from customer_revenue r

    inner join current_customers c
        on r.customer_unique_id = c.customer_unique_id

)

select *
from final

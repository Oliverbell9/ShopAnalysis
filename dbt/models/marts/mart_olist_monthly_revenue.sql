{{ config(materialized='table') }}

with delivered_orders as (

    select
        order_id,
        cast(date_trunc('month', order_purchased_at) as date)
            as purchase_month,
        merchandise_value,
        freight_value,
        gross_order_value

    from {{ ref('fct_olist_orders') }}

    where order_status = 'delivered'

),

monthly as (

    select
        purchase_month,
        count(*) as delivered_orders,
        sum(merchandise_value) as gross_merchandise_revenue,
        sum(freight_value) as freight_value,
        sum(gross_order_value) as gross_order_value

    from delivered_orders

    group by purchase_month

),

final as (

    select
        purchase_month,
        delivered_orders,
        gross_merchandise_revenue,
        freight_value,
        gross_order_value,
        cast(
            gross_order_value / nullif(delivered_orders, 0)
            as decimal(18,2)
        ) as average_gross_order_value

    from monthly

)

select *
from final

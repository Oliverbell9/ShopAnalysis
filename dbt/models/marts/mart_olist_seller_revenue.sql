{{ config(materialized='table') }}

with delivered_items as (

    select
        order_id,
        order_item_id,
        seller_id,
        merchandise_value,
        freight_value,
        item_gross_value

    from {{ ref('fct_olist_order_items') }}

    where is_delivered = true

),

seller_attributes as (

    select
        seller_id,
        seller_city,
        seller_state,
        seller_zip_code_prefix

    from {{ ref('dim_seller') }}

),

seller_revenue as (

    select
        s.seller_id,
        s.seller_city,
        s.seller_state,
        s.seller_zip_code_prefix,

        count(*) as delivered_item_rows,

        count(distinct i.order_id)
            as distinct_delivered_orders,

        sum(i.merchandise_value)
            as gross_merchandise_revenue,

        sum(i.freight_value)
            as freight_value,

        sum(i.item_gross_value)
            as gross_order_value

    from delivered_items i

    inner join seller_attributes s
        on i.seller_id = s.seller_id

    group by
        s.seller_id,
        s.seller_city,
        s.seller_state,
        s.seller_zip_code_prefix

)

select *
from seller_revenue

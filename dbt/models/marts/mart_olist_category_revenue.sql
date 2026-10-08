{{ config(materialized='table') }}

with delivered_items as (

    select
        i.order_id,
        i.order_item_id,
        i.product_id,
        i.merchandise_value,
        i.freight_value,
        i.item_gross_value

    from {{ ref('fct_olist_order_items') }} i

    where i.is_delivered = true

),

categorized_items as (

    select
        i.order_id,
        i.order_item_id,
        p.product_category_name,
        p.product_category_name_english,
        p.category_translation_status,
        i.merchandise_value,
        i.freight_value,
        i.item_gross_value

    from delivered_items i

    inner join {{ ref('dim_product') }} p
        on i.product_id = p.product_id

),

final as (

    select
        product_category_name,
        product_category_name_english,
        category_translation_status,

        count(*) as delivered_item_rows,
        count(distinct order_id) as distinct_delivered_orders,

        sum(merchandise_value) as gross_merchandise_revenue,
        sum(freight_value) as freight_value,
        sum(item_gross_value) as gross_order_value

    from categorized_items

    group by
        product_category_name,
        product_category_name_english,
        category_translation_status

)

select *
from final

with order_control as (

    select
        count(*) as delivered_orders
    from {{ ref('fct_olist_orders') }}
    where is_delivered = true

),

item_control as (

    select
        count(*) as delivered_items,
        count(distinct order_id) as distinct_orders
    from {{ ref('fct_olist_order_items') }}
    where is_delivered = true

),

seller_attribution as (

    select
        count(*) as seller_order_attributions
    from (
        select distinct
            order_id,
            seller_id
        from {{ ref('fct_olist_order_items') }}
        where is_delivered = true
    ) seller_orders

),

category_attribution as (

    select
        count(*) as category_order_attributions
    from (
        select distinct
            i.order_id,
            p.product_category_name,
            p.product_category_name_english,
            p.category_translation_status
        from {{ ref('fct_olist_order_items') }} i
        inner join {{ ref('dim_product') }} p
            on i.product_id = p.product_id
        where i.is_delivered = true
    ) category_orders

),

mart_counts as (

    select
        (select sum(delivered_orders)
         from {{ ref('mart_olist_monthly_revenue') }})
            as monthly_orders,

        (select sum(delivered_orders)
         from {{ ref('mart_olist_customer_revenue') }})
            as customer_orders,

        (select sum(delivered_item_rows)
         from {{ ref('mart_olist_seller_revenue') }})
            as seller_items,

        (select sum(distinct_delivered_orders)
         from {{ ref('mart_olist_seller_revenue') }})
            as seller_order_attributions,

        (select sum(delivered_item_rows)
         from {{ ref('mart_olist_category_revenue') }})
            as category_items,

        (select sum(distinct_delivered_orders)
         from {{ ref('mart_olist_category_revenue') }})
            as category_order_attributions

)

select
    o.delivered_orders as source_orders,
    i.delivered_items as source_items,
    i.distinct_orders as item_distinct_orders,
    m.*

from order_control o
cross join item_control i
cross join seller_attribution s
cross join category_attribution c
cross join mart_counts m

where o.delivered_orders is distinct from i.distinct_orders
   or m.monthly_orders is distinct from o.delivered_orders
   or m.customer_orders is distinct from o.delivered_orders
   or m.seller_items is distinct from i.delivered_items
   or m.category_items is distinct from i.delivered_items
   or m.seller_order_attributions
        is distinct from s.seller_order_attributions
   or m.category_order_attributions
        is distinct from c.category_order_attributions

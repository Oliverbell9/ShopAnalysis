with seller_checks as (

    select
        seller_id,
        count(*) as row_count,
        max(delivered_item_rows) as item_rows,
        max(distinct_delivered_orders) as order_count,
        max(gross_merchandise_revenue) as merchandise,
        max(freight_value) as freight,
        max(gross_order_value) as gross

    from {{ ref('mart_olist_seller_revenue') }}

    group by seller_id

)

select *
from seller_checks

where seller_id is null
   or row_count <> 1
   or item_rows <= 0
   or order_count <= 0
   or order_count > item_rows
   or gross is distinct from merchandise + freight

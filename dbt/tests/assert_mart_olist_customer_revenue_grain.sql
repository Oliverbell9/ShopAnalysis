with customer_checks as (

    select
        customer_unique_id,
        count(*) as row_count,
        max(delivered_orders) as order_count,
        max(first_delivered_purchase_at) as first_purchase_at,
        max(last_delivered_purchase_at) as last_purchase_at,
        max(purchase_span_days) as span_days,
        max(gross_merchandise_revenue) as merchandise,
        max(freight_value) as freight,
        max(gross_order_value) as gross

    from {{ ref('mart_olist_customer_revenue') }}

    group by customer_unique_id

)

select *
from customer_checks

where customer_unique_id is null
   or row_count <> 1
   or order_count <= 0
   or first_purchase_at > last_purchase_at
   or span_days < 0
   or gross is distinct from merchandise + freight

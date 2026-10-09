with source_control as (

    select
        sum(merchandise_value) as merchandise,
        sum(freight_value) as freight,
        sum(gross_order_value) as gross
    from {{ ref('fct_olist_orders') }}
    where is_delivered = true

),

mart_totals as (

    select
        'monthly' as mart,
        sum(gross_merchandise_revenue) as merchandise,
        sum(freight_value) as freight,
        sum(gross_order_value) as gross
    from {{ ref('mart_olist_monthly_revenue') }}

    union all

    select
        'category' as mart,
        sum(gross_merchandise_revenue) as merchandise,
        sum(freight_value) as freight,
        sum(gross_order_value) as gross
    from {{ ref('mart_olist_category_revenue') }}

    union all

    select
        'seller' as mart,
        sum(gross_merchandise_revenue) as merchandise,
        sum(freight_value) as freight,
        sum(gross_order_value) as gross
    from {{ ref('mart_olist_seller_revenue') }}

    union all

    select
        'customer' as mart,
        sum(gross_merchandise_revenue) as merchandise,
        sum(freight_value) as freight,
        sum(gross_order_value) as gross
    from {{ ref('mart_olist_customer_revenue') }}

)

select
    m.mart,
    m.merchandise as actual_merchandise,
    s.merchandise as expected_merchandise,
    m.freight as actual_freight,
    s.freight as expected_freight,
    m.gross as actual_gross,
    s.gross as expected_gross

from mart_totals m
cross join source_control s

where m.merchandise is distinct from s.merchandise
   or m.freight is distinct from s.freight
   or m.gross is distinct from s.gross

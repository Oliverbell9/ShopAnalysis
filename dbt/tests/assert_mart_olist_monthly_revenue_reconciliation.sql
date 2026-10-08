-- Reconcile monthly delivered-order analytics to the governed order fact.
-- Expected result: zero rows.

with expected as (

    select
        cast(date_trunc('month', order_purchased_at) as date)
            as purchase_month,
        count(*) as delivered_orders,
        sum(merchandise_value) as gross_merchandise_revenue,
        sum(freight_value) as freight_value,
        sum(gross_order_value) as gross_order_value,
        cast(
            sum(gross_order_value) / nullif(count(*), 0)
            as decimal(18,2)
        ) as average_gross_order_value

    from {{ ref('fct_olist_orders') }}

    where order_status = 'delivered'

    group by 1

),

actual as (

    select *
    from {{ ref('mart_olist_monthly_revenue') }}

),

differences as (

    select
        coalesce(e.purchase_month, a.purchase_month) as purchase_month,

        case
            when e.purchase_month is null then 'unexpected_month'
            when a.purchase_month is null then 'missing_month'
            else 'metric_mismatch'
        end as violation

    from expected e

    full outer join actual a
        on e.purchase_month = a.purchase_month

    where e.purchase_month is null
       or a.purchase_month is null
       or e.delivered_orders is distinct from a.delivered_orders
       or e.gross_merchandise_revenue
            is distinct from a.gross_merchandise_revenue
       or e.freight_value is distinct from a.freight_value
       or e.gross_order_value is distinct from a.gross_order_value
       or e.average_gross_order_value
            is distinct from a.average_gross_order_value

)

select *
from differences

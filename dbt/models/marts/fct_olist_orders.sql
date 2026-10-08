{{ config(materialized='table') }}

with orders as (

    select *
    from {{ ref('int_olist__orders_enriched') }}

),

reconciliation as (

    select
        order_id,
        reconciliation_status,
        payment_item_difference
    from {{ ref('int_olist__order_reconciliation') }}

),

final as (

    select
        o.order_id,
        o.customer_id,
        o.customer_unique_id,
        d.customer_sk,

        o.order_status,

        o.order_purchased_at,
        o.order_approved_at,
        o.delivered_to_carrier_at,
        o.delivered_to_customer_at,
        o.estimated_delivery_at,

        o.customer_zip_code_prefix,
        o.customer_city,
        o.customer_state,

        o.item_count,

        o.item_revenue as merchandise_value,
        o.freight_revenue as freight_value,
        o.item_plus_freight as gross_order_value,

        o.payment_record_count,
        o.payment_type_count,
        o.payment_value,

        o.review_record_count,
        o.distinct_review_count,
        o.average_review_score,

        r.payment_item_difference,
        r.reconciliation_status,

        case
            when o.order_status = 'delivered'
                then true
            else false
        end as is_delivered,

        case
            when o.order_status = 'delivered'
             and o.delivered_to_customer_at is null
                then true
            else false
        end as is_delivery_timestamp_exception

    from orders o

    inner join reconciliation r
        on o.order_id = r.order_id

    inner join {{ ref('dim_customer') }} d
        on o.customer_unique_id = d.customer_unique_id
       and o.order_purchased_at >= d.valid_from
       and (
            o.order_purchased_at < d.valid_to
            or d.valid_to is null
       )

)

select *
from final

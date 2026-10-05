with orders as (

    select *
    from {{ ref('int_olist__orders_enriched') }}

),

reconciled as (

    select
        order_id,
        customer_id,
        customer_unique_id,
        order_status,
        order_purchased_at,

        item_count,
        payment_record_count,
        payment_type_count,
        max_payment_sequence,
        max_payment_installments,

        item_revenue,
        freight_revenue,
        item_plus_freight,
        payment_value,

        case
            when item_plus_freight is not null
             and payment_value is not null
                then payment_value - item_plus_freight
            else null
        end as payment_item_difference,

        case
            when item_plus_freight is null
                then 'missing_items'

            when payment_value is null
                then 'missing_payment'

            when payment_value = item_plus_freight
                then 'exact_match'

            when abs(payment_value - item_plus_freight) <= 0.01
                then 'within_one_cent'

            when payment_value - item_plus_freight > 0.01
                then 'payment_above_item_plus_freight'

            when payment_value - item_plus_freight < -0.01
                then 'payment_below_item_plus_freight'

            else 'unclassified'
        end as reconciliation_status

    from orders

)

select *
from reconciled

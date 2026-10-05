with orders as (

    select *
    from {{ ref('stg_olist__orders') }}

),

customers as (

    select *
    from {{ ref('stg_olist__customers') }}

),

order_items as (

    select *
    from {{ ref('int_olist__order_items_by_order') }}

),

payments as (

    select *
    from {{ ref('int_olist__payments_by_order') }}

),

reviews as (

    select *
    from {{ ref('int_olist__reviews_by_order') }}

),

enriched as (

    select
        orders.order_id,
        orders.customer_id,
        customers.customer_unique_id,

        customers.customer_zip_code_prefix,
        customers.customer_city,
        customers.customer_state,

        orders.order_status,
        orders.order_purchased_at,
        orders.order_approved_at,
        orders.delivered_to_carrier_at,
        orders.delivered_to_customer_at,
        orders.estimated_delivery_at,

        order_items.item_count,
        order_items.distinct_product_count,
        order_items.distinct_seller_count,
        order_items.item_revenue,
        order_items.freight_revenue,
        order_items.item_plus_freight,
        order_items.first_shipping_limit_at,
        order_items.last_shipping_limit_at,

        payments.payment_record_count,
        payments.payment_type_count,
        payments.max_payment_sequence,
        payments.max_payment_installments,
        payments.payment_value,

        reviews.review_record_count,
        reviews.distinct_review_count,
        reviews.minimum_review_score,
        reviews.maximum_review_score,
        reviews.average_review_score,
        reviews.first_review_created_at,
        reviews.last_review_created_at,
        reviews.last_review_answered_at

    from orders

    left join customers
        on orders.customer_id = customers.customer_id

    left join order_items
        on orders.order_id = order_items.order_id

    left join payments
        on orders.order_id = payments.order_id

    left join reviews
        on orders.order_id = reviews.order_id

)

select *
from enriched

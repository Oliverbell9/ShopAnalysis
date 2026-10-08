-- Verify source coverage, item attributes, and financial measures.
-- Expected result: zero rows.

with expected as (

    select
        i.order_id,
        i.order_item_id,
        i.product_id,
        i.seller_id,
        o.order_purchased_at,
        o.order_status,
        o.is_delivered,
        i.shipping_limit_at,
        i.price as merchandise_value,
        i.freight_value,
        i.price + i.freight_value as item_gross_value

    from {{ ref('stg_olist__order_items') }} i

    inner join {{ ref('fct_olist_orders') }} o
        on i.order_id = o.order_id

),

actual as (

    select *
    from {{ ref('fct_olist_order_items') }}

),

missing_or_mismatched as (

    select
        e.order_id,
        e.order_item_id

    from expected e

    left join actual a
        on e.order_id = a.order_id
       and e.order_item_id = a.order_item_id

    where a.order_id is null
       or e.product_id is distinct from a.product_id
       or e.seller_id is distinct from a.seller_id
       or e.order_purchased_at is distinct from a.order_purchased_at
       or e.order_status is distinct from a.order_status
       or e.is_delivered is distinct from a.is_delivered
       or e.shipping_limit_at is distinct from a.shipping_limit_at
       or e.merchandise_value is distinct from a.merchandise_value
       or e.freight_value is distinct from a.freight_value
       or e.item_gross_value is distinct from a.item_gross_value

),

unexpected_items as (

    select
        a.order_id,
        a.order_item_id

    from actual a

    left join expected e
        on a.order_id = e.order_id
       and a.order_item_id = e.order_item_id

    where e.order_id is null

)

select
    order_id,
    order_item_id,
    'missing_or_mismatched' as violation
from missing_or_mismatched

union all

select
    order_id,
    order_item_id,
    'unexpected_item' as violation
from unexpected_items

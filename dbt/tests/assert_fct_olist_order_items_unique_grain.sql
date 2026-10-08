-- Assert one fact row per (order_id, order_item_id).
-- Expected result: zero rows.

select
    order_id,
    order_item_id,
    count(*) as duplicate_count

from {{ ref('fct_olist_order_items') }}

group by
    order_id,
    order_item_id

having count(*) > 1

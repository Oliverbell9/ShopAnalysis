with expected as (

    select
        p.product_category_name,
        p.product_category_name_english,
        p.category_translation_status,
        count(*) as delivered_item_rows,
        count(distinct i.order_id) as distinct_delivered_orders

    from {{ ref('fct_olist_order_items') }} i

    inner join {{ ref('dim_product') }} p
        on i.product_id = p.product_id

    where i.is_delivered = true

    group by
        p.product_category_name,
        p.product_category_name_english,
        p.category_translation_status

),

actual as (

    select
        product_category_name,
        product_category_name_english,
        category_translation_status,
        delivered_item_rows,
        distinct_delivered_orders

    from {{ ref('mart_olist_category_revenue') }}

),

differences as (

    (
        select * from expected
        except all
        select * from actual
    )

    union all

    (
        select * from actual
        except all
        select * from expected
    )

)

select *
from differences

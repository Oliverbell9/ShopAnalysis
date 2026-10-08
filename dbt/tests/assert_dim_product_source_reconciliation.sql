-- Verify product dimension coverage, attributes, and category classification.
-- Expected result: zero rows.

with expected as (

    select
        p.product_id,
        p.product_category_name,
        t.product_category_name_english,

        case
            when p.product_category_name is null
                then 'missing_source_category'
            when t.product_category_name is null
                then 'unmatched_translation'
            when t.product_category_name_english is null
                then 'missing_english_translation'
            else 'translated'
        end as expected_status,

        p.product_name_length,
        p.product_description_length,
        p.product_photos_quantity,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm

    from {{ ref('stg_olist__products') }} p

    left join {{ ref('stg_olist__translation') }} t
        on p.product_category_name = t.product_category_name

),

actual as (

    select *
    from {{ ref('dim_product') }}

),

missing_or_mismatched as (

    select
        e.product_id

    from expected e

    left join actual a
        on e.product_id = a.product_id

    where a.product_id is null
       or e.product_category_name is distinct from a.product_category_name
       or e.product_category_name_english is distinct from a.product_category_name_english
       or e.expected_status is distinct from a.category_translation_status
       or e.product_name_length is distinct from a.product_name_length
       or e.product_description_length is distinct from a.product_description_length
       or e.product_photos_quantity is distinct from a.product_photos_quantity
       or e.product_weight_g is distinct from a.product_weight_g
       or e.product_length_cm is distinct from a.product_length_cm
       or e.product_height_cm is distinct from a.product_height_cm
       or e.product_width_cm is distinct from a.product_width_cm

),

unexpected_products as (

    select
        a.product_id

    from actual a

    left join expected e
        on a.product_id = e.product_id

    where e.product_id is null

)

select product_id, 'missing_or_mismatched' as violation
from missing_or_mismatched

union all

select product_id, 'unexpected_product' as violation
from unexpected_products

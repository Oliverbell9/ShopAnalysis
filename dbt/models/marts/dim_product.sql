{{ config(materialized='table') }}

with products as (

    select *
    from {{ ref('stg_olist__products') }}

),

translations as (

    select *
    from {{ ref('stg_olist__translation') }}

),

joined as (

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
        end as category_translation_status,

        p.product_name_length,
        p.product_description_length,
        p.product_photos_quantity,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm

    from products p

    left join translations t
        on p.product_category_name = t.product_category_name

)

select *
from joined

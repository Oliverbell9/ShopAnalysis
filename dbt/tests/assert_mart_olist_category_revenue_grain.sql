-- Expected result: zero rows.
-- Check category-grain uniqueness and translation consistency.

with grain_duplicates as (

    select
        product_category_name
    from {{ ref('mart_olist_category_revenue') }}
    group by product_category_name
    having count(*) > 1

),

invalid_translation as (

    select
        product_category_name
    from {{ ref('mart_olist_category_revenue') }}
    where
        (
            category_translation_status = 'translated'
            and (
                product_category_name is null
                or product_category_name_english is null
            )
        )
        or
        (
            category_translation_status = 'missing_source_category'
            and (
                product_category_name is not null
                or product_category_name_english is not null
            )
        )
        or
        (
            category_translation_status = 'unmatched_translation'
            and (
                product_category_name is null
                or product_category_name_english is not null
            )
        )

)

select
    'duplicate_category' as violation,
    product_category_name
from grain_duplicates

union all

select
    'invalid_translation' as violation,
    product_category_name
from invalid_translation

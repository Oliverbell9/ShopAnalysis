-- Verify seller dimension coverage and source attribute preservation.
-- Expected result: zero rows.

with expected as (

    select
        seller_id,
        seller_zip_code_prefix,
        seller_city,
        seller_state

    from {{ ref('stg_olist__sellers') }}

),

actual as (

    select *
    from {{ ref('dim_seller') }}

),

missing_or_mismatched as (

    select
        e.seller_id

    from expected e

    left join actual a
        on e.seller_id = a.seller_id

    where a.seller_id is null
       or e.seller_zip_code_prefix is distinct from a.seller_zip_code_prefix
       or e.seller_city is distinct from a.seller_city
       or e.seller_state is distinct from a.seller_state

),

unexpected_sellers as (

    select
        a.seller_id

    from actual a

    left join expected e
        on a.seller_id = e.seller_id

    where e.seller_id is null

)

select seller_id, 'missing_or_mismatched' as violation
from missing_or_mismatched

union all

select seller_id, 'unexpected_seller' as violation
from unexpected_sellers

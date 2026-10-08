{{ config(materialized='table') }}

with sellers as (

    select *
    from {{ ref('stg_olist__sellers') }}

),

final as (

    select
        seller_id,
        seller_zip_code_prefix,
        seller_city,
        seller_state

    from sellers

)

select *
from final

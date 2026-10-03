with source as (

    select *
    from {{ source('olist_raw', 'olist_sellers') }}

),

renamed as (

    select
        cast(seller_id as varchar) as seller_id,
        cast(seller_zip_code_prefix as bigint) as seller_zip_code_prefix,
        cast(seller_city as varchar) as seller_city,
        cast(seller_state as varchar) as seller_state,

        cast(_source_file as varchar) as _source_file,
        cast(_file_row_number as bigint) as _file_row_number,
        _loaded_at,
        cast(_batch_id as varchar) as _batch_id

    from source

),

deduplicated as (

    select *
    from renamed
    qualify row_number() over (
        partition by seller_id
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated

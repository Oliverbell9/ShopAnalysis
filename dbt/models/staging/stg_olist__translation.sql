with source as (

    select *
    from {{ source('olist_raw', 'olist_translation') }}

),

renamed as (

    select
        cast(product_category_name as varchar) as product_category_name,
        cast(product_category_name_english as varchar) as product_category_name_english,

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
        partition by product_category_name
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated

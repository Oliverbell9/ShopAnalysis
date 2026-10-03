with source as (

    select *
    from {{ source('olist_raw', 'olist_products') }}

),

renamed as (

    select
        cast(product_id as varchar) as product_id,
        cast(product_category_name as varchar) as product_category_name,
        cast(product_name_lenght as bigint) as product_name_length,
        cast(product_description_lenght as bigint) as product_description_length,
        cast(product_photos_qty as bigint) as product_photos_quantity,
        cast(product_weight_g as bigint) as product_weight_g,
        cast(product_length_cm as bigint) as product_length_cm,
        cast(product_height_cm as bigint) as product_height_cm,
        cast(product_width_cm as bigint) as product_width_cm,

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
        partition by product_id
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated

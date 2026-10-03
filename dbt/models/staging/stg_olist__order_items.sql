with source as (

    select *
    from {{ source('olist_raw', 'olist_order_items') }}

),

renamed as (

    select
        cast(order_id as varchar) as order_id,
        cast(order_item_id as bigint) as order_item_id,
        cast(product_id as varchar) as product_id,
        cast(seller_id as varchar) as seller_id,
        cast(shipping_limit_date as timestamp) as shipping_limit_at,
        cast(price as double) as price,
        cast(freight_value as double) as freight_value,

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
        partition by order_id, order_item_id
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated

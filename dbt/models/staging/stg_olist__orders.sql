with source as (

    select *
    from {{ source('olist_raw', 'olist_orders') }}

),

renamed as (

    select
        cast(order_id as varchar) as order_id,
        cast(customer_id as varchar) as customer_id,
        cast(order_status as varchar) as order_status,
        cast(order_purchase_timestamp as timestamp) as order_purchased_at,
        cast(order_approved_at as timestamp) as order_approved_at,
        cast(order_delivered_carrier_date as timestamp) as delivered_to_carrier_at,
        cast(order_delivered_customer_date as timestamp) as delivered_to_customer_at,
        cast(order_estimated_delivery_date as timestamp) as estimated_delivery_at,

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
        partition by order_id
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated

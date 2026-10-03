with source as (

    select *
    from {{ source('olist_raw', 'olist_payments') }}

),

renamed as (

    select
        cast(order_id as varchar) as order_id,
        cast(payment_sequential as bigint) as payment_sequence,
        cast(payment_type as varchar) as payment_type,
        cast(payment_installments as bigint) as payment_installments,
        cast(payment_value as decimal(18,2)) as payment_value,

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
        partition by order_id, payment_sequence
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated

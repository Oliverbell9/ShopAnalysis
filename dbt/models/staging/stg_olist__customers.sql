with source as (

    select *
    from {{ source('olist_raw', 'olist_customers') }}

),

renamed as (

    select
        cast(customer_id as varchar) as customer_id,
        cast(customer_unique_id as varchar) as customer_unique_id,
        cast(customer_zip_code_prefix as bigint) as customer_zip_code_prefix,
        cast(customer_city as varchar) as customer_city,
        cast(customer_state as varchar) as customer_state,

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
        partition by customer_id
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated
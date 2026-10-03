with source as (

    select *
    from {{ source('olist_raw', 'olist_geolocation') }}

),

renamed as (

    select
        cast(geolocation_zip_code_prefix as bigint) as geolocation_zip_code_prefix,
        cast(geolocation_lat as double) as geolocation_latitude,
        cast(geolocation_lng as double) as geolocation_longitude,
        cast(geolocation_city as varchar) as geolocation_city,
        cast(geolocation_state as varchar) as geolocation_state,

        cast(_source_file as varchar) as _source_file,
        cast(_file_row_number as bigint) as _file_row_number,
        _loaded_at,
        cast(_batch_id as varchar) as _batch_id

    from source

)

select *
from renamed

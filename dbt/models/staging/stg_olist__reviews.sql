with source as (

    select *
    from {{ source('olist_raw', 'olist_reviews') }}

),

renamed as (

    select
        cast(review_id as varchar) as review_id,
        cast(order_id as varchar) as order_id,
        cast(review_score as bigint) as review_score,
        cast(review_comment_title as varchar) as review_comment_title,
        cast(review_comment_message as varchar) as review_comment_message,
        cast(review_creation_date as timestamp) as review_created_at,
        cast(review_answer_timestamp as timestamp) as review_answered_at,

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
        partition by review_id, order_id
        order by _loaded_at desc, _file_row_number desc
    ) = 1

)

select *
from deduplicated

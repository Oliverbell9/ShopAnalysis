with reviews as (

    select *
    from {{ ref('stg_olist__reviews') }}

),

aggregated as (

    select
        order_id,

        count(*) as review_record_count,
        count(distinct review_id) as distinct_review_count,

        min(review_score) as minimum_review_score,
        max(review_score) as maximum_review_score,
        avg(review_score) as average_review_score,

        min(review_created_at) as first_review_created_at,
        max(review_created_at) as last_review_created_at,
        max(review_answered_at) as last_review_answered_at

    from reviews
    group by order_id

)

select *
from aggregated

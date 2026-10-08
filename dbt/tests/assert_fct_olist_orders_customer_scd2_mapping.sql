with invalid_customer_mapping as (

    select
        f.order_id
    from {{ ref('fct_olist_orders') }} f

    left join {{ ref('dim_customer') }} d
        on f.customer_sk = d.customer_sk

    where d.customer_sk is null
       or f.customer_unique_id is distinct from d.customer_unique_id
       or f.order_purchased_at < d.valid_from
       or (
            d.valid_to is not null
            and f.order_purchased_at >= d.valid_to
       )

),

ambiguous_historical_matches as (

    select
        f.order_id
    from {{ ref('fct_olist_orders') }} f

    left join {{ ref('dim_customer') }} d
        on f.customer_unique_id = d.customer_unique_id
       and f.order_purchased_at >= d.valid_from
       and (
            f.order_purchased_at < d.valid_to
            or d.valid_to is null
       )

    group by f.order_id
    having count(d.customer_sk) <> 1

)

select order_id
from invalid_customer_mapping

union

select order_id
from ambiguous_historical_matches

with payments as (

    select *
    from {{ ref('stg_olist__payments') }}

),

aggregated as (

    select
        order_id,

        count(*) as payment_record_count,
        count(distinct payment_type) as payment_type_count,
        max(payment_sequence) as max_payment_sequence,
        max(payment_installments) as max_payment_installments,

        sum(payment_value) as payment_value

    from payments
    group by order_id

)

select *
from aggregated

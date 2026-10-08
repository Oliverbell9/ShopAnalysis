{{ config(materialized='table') }}

with customer_orders as (

    select
        customer_unique_id,
        order_id,
        order_purchased_at,
        customer_zip_code_prefix,
        customer_city,
        customer_state
    from {{ ref('int_olist__orders_enriched') }}

),

ordered_history as (

    select
        *,

        lag(customer_zip_code_prefix) over (
            partition by customer_unique_id
            order by order_purchased_at, order_id
        ) as previous_zip_code_prefix,

        lag(customer_city) over (
            partition by customer_unique_id
            order by order_purchased_at, order_id
        ) as previous_city,

        lag(customer_state) over (
            partition by customer_unique_id
            order by order_purchased_at, order_id
        ) as previous_state,

        row_number() over (
            partition by customer_unique_id
            order by order_purchased_at, order_id
        ) as customer_order_sequence

    from customer_orders

),

change_detection as (

    select
        *,

        case
            when customer_order_sequence = 1 then 1

            when customer_zip_code_prefix
                    is distinct from previous_zip_code_prefix
              or customer_city
                    is distinct from previous_city
              or customer_state
                    is distinct from previous_state
                then 1

            else 0
        end as starts_new_version

    from ordered_history

),

version_assignment as (

    select
        *,

        sum(starts_new_version) over (
            partition by customer_unique_id
            order by order_purchased_at, order_id
            rows between unbounded preceding and current row
        ) as customer_version

    from change_detection

),

version_rollup as (

    select
        customer_unique_id,
        customer_version,

        arg_min(
            customer_zip_code_prefix,
            struct_pack(
                purchased_at := order_purchased_at,
                order_id := order_id
            )
        ) as customer_zip_code_prefix,

        arg_min(
            customer_city,
            struct_pack(
                purchased_at := order_purchased_at,
                order_id := order_id
            )
        ) as customer_city,

        arg_min(
            customer_state,
            struct_pack(
                purchased_at := order_purchased_at,
                order_id := order_id
            )
        ) as customer_state,

        min(order_purchased_at) as valid_from,
        count(*) as orders_in_version

    from version_assignment

    group by
        customer_unique_id,
        customer_version

),

effective_dating as (

    select
        *,

        lead(valid_from) over (
            partition by customer_unique_id
            order by customer_version
        ) as valid_to

    from version_rollup

),

final as (

    select
        md5(
            customer_unique_id
            || '|'
            || cast(customer_version as varchar)
        ) as customer_sk,

        customer_unique_id,
        cast(customer_version as bigint) as customer_version,

        customer_zip_code_prefix,
        customer_city,
        customer_state,

        valid_from,
        valid_to,

        case
            when valid_to is null then true
            else false
        end as is_current,

        orders_in_version

    from effective_dating

)

select *
from final

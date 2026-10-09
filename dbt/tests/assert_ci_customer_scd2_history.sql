{{ config(enabled=target.name == 'ci') }}

with expected as (

    select *
    from (
        values
            (
                'CI-UNIQUE-A',
                1::bigint,
                10001::bigint,
                'city_a',
                'SP',
                timestamp '2025-01-01 10:00:00',
                timestamp '2025-02-01 10:00:00',
                false,
                1::bigint
            ),
            (
                'CI-UNIQUE-A',
                2::bigint,
                20002::bigint,
                'city_b',
                'RJ',
                timestamp '2025-02-01 10:00:00',
                null::timestamp,
                true,
                1::bigint
            )
    ) as t (
        customer_unique_id,
        customer_version,
        customer_zip_code_prefix,
        customer_city,
        customer_state,
        valid_from,
        valid_to,
        is_current,
        orders_in_version
    )

),

actual as (

    select
        customer_unique_id,
        customer_version,
        customer_zip_code_prefix,
        customer_city,
        customer_state,
        valid_from,
        valid_to,
        is_current,
        orders_in_version
    from {{ ref('dim_customer') }}
    where customer_unique_id = 'CI-UNIQUE-A'

),

differences as (

    (select * from expected except all select * from actual)
    union all
    (select * from actual except all select * from expected)

)

select *
from differences

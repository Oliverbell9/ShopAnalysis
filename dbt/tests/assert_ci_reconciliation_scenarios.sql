{{ config(enabled=target.name == 'ci') }}

with expected as (

    select *
    from (
        values
            ('CI-ORD-001', 'exact_match', 165.00, 165.00, 0.00),
            ('CI-ORD-002', 'within_one_cent', 22.00, 22.01, 0.01),
            ('CI-ORD-003', 'payment_above_item_plus_freight', 33.00, 40.00, 7.00),
            ('CI-ORD-004', 'payment_below_item_plus_freight', 44.00, 40.00, -4.00),
            ('CI-ORD-005', 'missing_payment', 55.00, null, null),
            ('CI-ORD-006', 'missing_items', null, 12.00, null),
            ('CI-ORD-007', 'exact_match', 77.00, 77.00, 0.00)
    ) as t (
        order_id,
        reconciliation_status,
        item_plus_freight,
        payment_value,
        payment_item_difference
    )

),

actual as (

    select
        order_id,
        reconciliation_status,
        item_plus_freight,
        payment_value,
        payment_item_difference
    from {{ ref('int_olist__order_reconciliation') }}

),

differences as (

    (select * from expected except all select * from actual)
    union all
    (select * from actual except all select * from expected)

)

select *
from differences

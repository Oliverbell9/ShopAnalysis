select
    order_id,
    item_plus_freight,
    payment_value,
    payment_item_difference,
    reconciliation_status

from {{ ref('int_olist__order_reconciliation') }}

where
       (reconciliation_status = 'missing_items'
        and item_plus_freight is not null)

    or (reconciliation_status = 'missing_payment'
        and (item_plus_freight is null or payment_value is not null))

    or (reconciliation_status = 'exact_match'
        and (
            item_plus_freight is null
            or payment_value is null
            or payment_item_difference <> 0
        ))

    or (reconciliation_status = 'within_one_cent'
        and (
            item_plus_freight is null
            or payment_value is null
            or payment_item_difference = 0
            or abs(payment_item_difference) > 0.01
        ))

    or (reconciliation_status = 'payment_above_item_plus_freight'
        and (
            payment_item_difference is null
            or payment_item_difference <= 0.01
        ))

    or (reconciliation_status = 'payment_below_item_plus_freight'
        and (
            payment_item_difference is null
            or payment_item_difference >= -0.01
        ))

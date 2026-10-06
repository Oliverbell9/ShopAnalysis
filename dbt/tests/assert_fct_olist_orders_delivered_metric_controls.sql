with controls as (

    select
        count(*) as delivered_orders,
        sum(merchandise_value) as merchandise_value,
        sum(freight_value) as freight_value,
        sum(gross_order_value) as gross_order_value,
        sum(
            case
                when is_delivery_timestamp_exception then 1
                else 0
            end
        ) as delivery_timestamp_exceptions

    from {{ ref('fct_olist_orders') }}

    where is_delivered = true

)

select *
from controls

where delivered_orders <> 96478
   or merchandise_value <> cast(13221498.11 as decimal(38, 2))
   or freight_value <> cast(2198275.64 as decimal(38, 2))
   or gross_order_value <> cast(15419773.75 as decimal(38, 2))
   or delivery_timestamp_exceptions <> 8

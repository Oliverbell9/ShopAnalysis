with source_orders as (

    select order_id
    from {{ ref('int_olist__orders_enriched') }}

),

reconciliation_orders as (

    select order_id
    from {{ ref('int_olist__order_reconciliation') }}

),

missing_from_reconciliation as (

    select order_id
    from source_orders

    except

    select order_id
    from reconciliation_orders

),

unexpected_in_reconciliation as (

    select order_id
    from reconciliation_orders

    except

    select order_id
    from source_orders

)

select order_id, 'missing_from_reconciliation' as issue
from missing_from_reconciliation

union all

select order_id, 'unexpected_in_reconciliation' as issue
from unexpected_in_reconciliation

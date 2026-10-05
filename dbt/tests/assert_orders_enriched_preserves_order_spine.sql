with source_orders as (

    select order_id
    from {{ ref('stg_olist__orders') }}

),

enriched_orders as (

    select order_id
    from {{ ref('int_olist__orders_enriched') }}

),

missing_from_enriched as (

    select order_id
    from source_orders

    except

    select order_id
    from enriched_orders

),

unexpected_in_enriched as (

    select order_id
    from enriched_orders

    except

    select order_id
    from source_orders

)

select order_id, 'missing_from_enriched' as issue
from missing_from_enriched

union all

select order_id, 'unexpected_in_enriched' as issue
from unexpected_in_enriched

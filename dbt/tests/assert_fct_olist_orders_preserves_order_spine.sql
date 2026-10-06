with source_orders as (

    select order_id
    from {{ ref('int_olist__orders_enriched') }}

),

mart_orders as (

    select order_id
    from {{ ref('fct_olist_orders') }}

),

missing_from_mart as (

    select order_id
    from source_orders

    except

    select order_id
    from mart_orders

),

unexpected_in_mart as (

    select order_id
    from mart_orders

    except

    select order_id
    from source_orders

)

select *
from missing_from_mart

union all

select *
from unexpected_in_mart

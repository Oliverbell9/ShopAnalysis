with dimension_summary as (

    select
        count(*) as dimension_rows,
        count(distinct customer_sk) as distinct_customer_sk,
        count(distinct customer_unique_id) as persistent_customers,
        sum(case when is_current then 1 else 0 end) as current_rows,
        sum(case when customer_version > 1 then 1 else 0 end)
            as noninitial_version_rows,
        max(customer_version) as max_customer_version,
        sum(orders_in_version) as represented_orders
    from {{ ref('dim_customer') }}

),

multiple_version_customers as (

    select
        count(*) as customers_with_multiple_versions
    from (
        select customer_unique_id
        from {{ ref('dim_customer') }}
        group by customer_unique_id
        having count(*) > 1
    )

),

current_row_violations as (

    select
        count(*) as violations
    from (
        select customer_unique_id
        from {{ ref('dim_customer') }}
        group by customer_unique_id
        having sum(case when is_current then 1 else 0 end) <> 1
    )

),

invalid_intervals as (

    select
        count(*) as violations
    from {{ ref('dim_customer') }}
    where valid_to is not null
      and valid_to <= valid_from

),

boundary_violations as (

    select
        count(*) as violations
    from (
        select
            customer_unique_id,
            valid_to,
            lead(valid_from) over (
                partition by customer_unique_id
                order by customer_version
            ) as next_valid_from
        from {{ ref('dim_customer') }}
    )
    where next_valid_from is not null
      and valid_to is distinct from next_valid_from

),

order_mapping_violations as (

    select
        count(*) as violations
    from (
        select
            o.order_id,
            count(d.customer_sk) as matched_versions
        from {{ ref('int_olist__orders_enriched') }} o
        left join {{ ref('dim_customer') }} d
            on o.customer_unique_id = d.customer_unique_id
           and o.order_purchased_at >= d.valid_from
           and (
                d.valid_to is null
                or o.order_purchased_at < d.valid_to
           )
        group by o.order_id
        having count(d.customer_sk) <> 1
    )

)

select *
from dimension_summary
cross join multiple_version_customers
cross join current_row_violations
cross join invalid_intervals
cross join boundary_violations
cross join order_mapping_violations

where dimension_rows <> 96355
   or distinct_customer_sk <> 96355
   or persistent_customers <> 96096
   or current_rows <> 96096
   or noninitial_version_rows <> 259
   or max_customer_version <> 4
   or represented_orders <> 99441
   or customers_with_multiple_versions <> 252
   or current_row_violations.violations <> 0
   or invalid_intervals.violations <> 0
   or boundary_violations.violations <> 0
   or order_mapping_violations.violations <> 0

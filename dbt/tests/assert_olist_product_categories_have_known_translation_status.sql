-- Govern the known Olist product-category translation exceptions.
--
-- Source contract:
--   maximum orphan rows: 13
--   portateis_cozinha_e_preparadores_de_alimentos: 10
--   pc_gamer: 3
--
-- The test fails if:
--   1. an undocumented unmatched category appears;
--   2. total unmatched product rows exceed 13; or
--   3. either known category exceeds its documented row count.
--
-- A reduction in these exception counts is permitted because upstream source
-- corrections should not cause the pipeline to fail.

with unmatched_categories as (

    select
        p.product_category_name

    from {{ ref('stg_olist__products') }} as p

    left join {{ ref('stg_olist__translation') }} as t
        on p.product_category_name = t.product_category_name

    where p.product_category_name is not null
      and t.product_category_name is null

),

category_counts as (

    select
        product_category_name,
        count(*) as orphan_rows

    from unmatched_categories

    group by product_category_name

),

violations as (

    select
        product_category_name,
        orphan_rows

    from category_counts

    where product_category_name not in (
        'portateis_cozinha_e_preparadores_de_alimentos',
        'pc_gamer'
    )

       or (
           product_category_name = 'portateis_cozinha_e_preparadores_de_alimentos'
           and orphan_rows > 10
       )

       or (
           product_category_name = 'pc_gamer'
           and orphan_rows > 3
       )

),

total_violation as (

    select
        '__TOTAL_ORPHAN_ROWS__' as product_category_name,
        count(*) as orphan_rows

    from unmatched_categories

    having count(*) > 13

)

select *
from violations

union all

select *
from total_violation
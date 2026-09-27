-- One row per membership per calendar month it was active.
with memberships as (
    select m.*, i.master_customer_id
    from {{ ref('stg_crm__memberships') }} m
    join {{ ref('int_customer_identity') }} i using (customer_id)
    where not i.is_test_account
),

months as (
    select cast(month_start as date) as month_start
    from generate_series(date '2025-01-01', date '2026-06-01', interval 1 month) t(month_start)
)

select
    m.membership_id,
    m.master_customer_id                                    as customer_id,
    m.location_id,
    m.plan_name,
    m.monthly_fee,
    mo.month_start,
    date_trunc('month', m.start_date) = mo.month_start      as is_new,
    coalesce(date_trunc('month', m.end_date) = mo.month_start, false) as is_churned
from memberships m
join months mo
  on mo.month_start >= date_trunc('month', m.start_date)
 and (m.end_date is null or mo.month_start <= date_trunc('month', m.end_date))

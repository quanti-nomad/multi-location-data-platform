-- The certified KPI table: one row per location per month it was open.
-- Every column here is defined in kpis/kpi_bible.yml.
with months as (
    select cast(month_start as date) as month_start
    from generate_series(date '2025-01-01', date '2026-06-01', interval 1 month) t(month_start)
),

-- A closed location stays in reporting until its last financial activity:
-- refunds can post weeks after a site closes, and that money must not vanish.
last_activity as (
    select location_id, max(date_trunc('month', payment_date)) as last_month
    from {{ ref('fct_payments') }} group by 1
),

spine as (
    select l.location_id, l.location_name, l.brand, l.ownership, l.franchisee_id, m.month_start
    from {{ ref('dim_location') }} l
    left join last_activity la using (location_id)
    join months m
      on m.month_start >= date_trunc('month', l.opened_on)
     and (l.closed_on is null
          or m.month_start <= greatest(date_trunc('month', l.closed_on), la.last_month))
),

revenue as (
    select location_id, date_trunc('month', payment_date) as month_start,
        sum(amount_cents)                                                        as net_revenue_cents,
        sum(case when revenue_stream = 'membership' then amount_cents else 0 end) as membership_revenue_cents,
        sum(case when revenue_stream = 'service' then amount_cents else 0 end)    as service_revenue_cents
    from {{ ref('fct_payments') }} group by 1, 2
),

visits as (
    select location_id, date_trunc('month', appointment_date) as month_start,
        count(*)                                        as appointments_scheduled,
        count(*) filter (where status = 'completed')    as completed_visits,
        count(*) filter (where status = 'no_show')      as no_shows
    from {{ ref('fct_appointments') }} group by 1, 2
),

members as (
    select location_id, month_start,
        count(*)                                        as active_members,
        count(*) filter (where is_new)                  as new_members,
        count(*) filter (where is_churned)              as churned_members
    from {{ ref('fct_membership_months') }} group by 1, 2
),

leads as (
    select location_id, date_trunc('month', lead_date) as month_start,
        count(*)                                        as leads,
        count(*) filter (where is_converted)            as converted_leads
    from {{ ref('fct_leads') }} group by 1, 2
)

select
    s.location_id,
    s.location_name,
    s.brand,
    s.ownership,
    s.franchisee_id,
    s.month_start,
    coalesce(r.net_revenue_cents, 0) / 100.0                                        as net_revenue,
    coalesce(r.membership_revenue_cents, 0) / 100.0                                 as membership_revenue,
    coalesce(r.service_revenue_cents, 0) / 100.0                                    as service_revenue,
    coalesce(v.appointments_scheduled, 0)                                           as appointments_scheduled,
    coalesce(v.completed_visits, 0)                                                 as completed_visits,
    coalesce(v.no_shows, 0)                                                         as no_shows,
    round(coalesce(v.no_shows, 0) / nullif(v.appointments_scheduled, 0), 4)         as no_show_rate,
    round(coalesce(r.service_revenue_cents, 0) / 100.0 / nullif(v.completed_visits, 0), 2) as revenue_per_visit,
    coalesce(mb.active_members, 0)                                                  as active_members,
    coalesce(mb.new_members, 0)                                                     as new_members,
    coalesce(mb.churned_members, 0)                                                 as churned_members,
    round(coalesce(mb.churned_members, 0)
          / nullif(coalesce(mb.active_members, 0) - coalesce(mb.new_members, 0), 0), 4) as member_churn_rate,
    coalesce(ld.leads, 0)                                                           as leads,
    coalesce(ld.converted_leads, 0)                                                 as converted_leads,
    round(coalesce(ld.converted_leads, 0) / nullif(ld.leads, 0), 4)                 as lead_conversion_rate
from spine s
left join revenue r  on r.location_id = s.location_id  and r.month_start = s.month_start
left join visits v   on v.location_id = s.location_id  and v.month_start = s.month_start
left join members mb on mb.location_id = s.location_id and mb.month_start = s.month_start
left join leads ld   on ld.location_id = s.location_id and ld.month_start = s.month_start

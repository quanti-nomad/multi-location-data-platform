-- The KPI table must account for every cent in the certified revenue ledger.
with kpi as (select round(sum(net_revenue) * 100) as cents from {{ ref('kpi_location_monthly') }}),
ledger as (select sum(amount_cents) as cents from {{ ref('fct_payments') }})
select k.cents as kpi_cents, l.cents as ledger_cents
from kpi k cross join ledger l
where k.cents <> l.cents

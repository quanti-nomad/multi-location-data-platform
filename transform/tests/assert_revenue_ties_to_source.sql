-- Certified revenue must equal the raw source, recomputed independently from
-- the text amounts, minus voids and test accounts. Returns a row only on mismatch.
with source_net as (
    select sum(cast(round(cast(replace(replace(trim(p.amount), '$', ''), ',', '') as decimal(14, 2)) * 100) as bigint)) as cents
    from {{ source('crm', 'crm_payments') }} p
    join {{ source('crm', 'crm_customers') }} c on c.customer_id = p.customer_id
    where p.payment_status <> 'void'
      and not (coalesce(lower(trim(c.email)) like '%@clinic-test.com', false)
               or coalesce(lower(c.first_name) = 'test', false))
),
certified as (select sum(amount_cents) as cents from {{ ref('fct_payments') }})

select s.cents as source_cents, c.cents as certified_cents
from source_net s cross join certified c
where s.cents is distinct from c.cents

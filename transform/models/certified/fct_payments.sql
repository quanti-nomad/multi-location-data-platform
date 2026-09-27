-- Net revenue ledger: settled sales and refunds, excluding voids and test accounts.
select
    p.payment_id,
    i.master_customer_id                    as customer_id,
    p.location_id,
    p.payment_type,
    case when p.payment_type = 'membership' then 'membership' else 'service' end as revenue_stream,
    p.amount_cents,
    p.amount_cents / 100.0                  as amount,
    cast(p.paid_at as date)                 as payment_date
from {{ ref('stg_crm__payments') }} p
join {{ ref('int_customer_identity') }} i using (customer_id)
where not p.is_void
  and not i.is_test_account

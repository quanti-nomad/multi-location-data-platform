select
    l.lead_id,
    l.location_id,
    l.channel,
    cast(l.created_at as date)          as lead_date,
    i.master_customer_id                as converted_customer_id,
    i.master_customer_id is not null    as is_converted
from {{ ref('stg_crm__leads') }} l
left join {{ ref('int_customer_identity') }} i
  on i.customer_id = l.converted_customer_id and not i.is_test_account

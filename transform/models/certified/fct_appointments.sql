select
    a.appointment_id,
    i.master_customer_id            as customer_id,
    a.location_id,
    a.service_id,
    s.service_category,
    cast(a.scheduled_at as date)    as appointment_date,
    a.status
from {{ ref('stg_crm__appointments') }} a
join {{ ref('int_customer_identity') }} i using (customer_id)
left join {{ ref('stg_crm__services') }} s using (service_id)
where not i.is_test_account

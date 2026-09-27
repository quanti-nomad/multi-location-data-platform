-- Resolve duplicate customer records: the same person registered twice with the
-- email typed differently. The earliest record becomes the master id.
select
    customer_id,
    case
        when email_normalized is null then customer_id
        else min(customer_id) over (partition by email_normalized)
    end as master_customer_id,
    email_normalized,
    is_test_account
from {{ ref('stg_crm__customers') }}

select
    cast(customer_id as integer)            as customer_id,
    first_name,
    last_name,
    nullif(lower(trim(email)), '')          as email_normalized,
    cast(home_location_id as integer)       as home_location_id,
    cast(created_at as timestamp)           as created_at,
    -- test accounts are created by staff for training and must never reach reporting.
    -- coalesce matters: a customer with no email must be flagged false, not null,
    -- or they silently fall out of every "not is_test_account" filter downstream.
    coalesce(lower(trim(email)) like '%@clinic-test.com', false)
        or coalesce(lower(first_name) = 'test', false)                  as is_test_account
from {{ source('crm', 'crm_customers') }}

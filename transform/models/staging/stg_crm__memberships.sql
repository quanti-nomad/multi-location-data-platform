select
    cast(membership_id as integer)          as membership_id,
    cast(customer_id as integer)            as customer_id,
    cast(location_id as integer)            as location_id,
    plan_name,
    cast(monthly_fee as decimal(10, 2))     as monthly_fee,
    cast(start_date as date)                as start_date,
    cast(end_date as date)                  as end_date
from {{ source('crm', 'crm_memberships') }}

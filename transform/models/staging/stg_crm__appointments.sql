with src as (
    select *, lower(replace(replace(trim(status), '-', ''), ' ', '')) as status_key
    from {{ source('crm', 'crm_appointments') }}
)

select
    cast(appointment_id as integer)     as appointment_id,
    cast(customer_id as integer)        as customer_id,
    cast(location_id as integer)        as location_id,
    cast(service_id as integer)         as service_id,
    cast(scheduled_at as timestamp)     as scheduled_at,
    -- five spellings of three statuses collapse to one controlled vocabulary;
    -- anything new and unmapped becomes null and fails the not_null test
    case
        when status_key in ('completed', 'complete')  then 'completed'
        when status_key in ('cancelled', 'canceled')  then 'cancelled'
        when status_key = 'noshow'                     then 'no_show'
    end                                 as status,
    status                              as status_raw
from src

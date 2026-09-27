select
    cast(payment_id as integer)         as payment_id,
    cast(customer_id as integer)        as customer_id,
    cast(location_id as integer)        as location_id,
    cast(appointment_id as integer)     as appointment_id,
    cast(membership_id as integer)      as membership_id,
    payment_type,
    {{ to_cents('amount') }}            as amount_cents,
    payment_status = 'void'             as is_void,
    cast(paid_at as timestamp)          as paid_at
from {{ source('crm', 'crm_payments') }}

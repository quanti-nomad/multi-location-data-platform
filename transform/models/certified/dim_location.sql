select
    location_id,
    location_name,
    city,
    brand,
    ownership,
    franchisee_id,
    opened_on,
    closed_on,
    is_active
from {{ ref('stg_crm__locations') }}

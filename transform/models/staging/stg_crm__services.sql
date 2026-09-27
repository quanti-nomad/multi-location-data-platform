select
    cast(service_id as integer)         as service_id,
    service_name,
    category                            as service_category,
    cast(list_price as decimal(10, 2))  as list_price
from {{ source('crm', 'crm_services') }}

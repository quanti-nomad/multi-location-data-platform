with src as (select * from {{ source('crm', 'crm_locations') }}),

parsed as (
    select
        cast(location_id as integer)                                    as location_id,
        brand,
        ownership,
        franchisee_id,
        -- source names arrive with stray spaces and mixed casing
        {{ proper_case("trim(split_part(trim(location_name), ' - ', 2))") }} as city,
        cast(opened_on as date)                                         as opened_on,
        cast(closed_on as date)                                         as closed_on
    from src
)

select
    location_id,
    split_part(brand, ' ', 1) || ' - ' || city as location_name,
    city,
    brand,
    ownership,
    franchisee_id,
    opened_on,
    closed_on,
    closed_on is null                          as is_active
from parsed

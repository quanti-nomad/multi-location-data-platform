with src as (select *, lower(trim(lead_source)) as source_key from {{ source('crm', 'crm_leads') }})

select
    cast(lead_id as integer)                as lead_id,
    cast(location_id as integer)            as location_id,
    lead_source                             as lead_source_raw,
    case
        when source_key in ('google ads', 'google', 'adwords')                 then 'paid_search'
        when source_key in ('facebook ads', 'fb', 'facebook', 'instagram', 'ig') then 'paid_social'
        when source_key in ('referral', 'friend')                              then 'referral'
        when source_key in ('website', 'organic', 'seo')                       then 'organic'
        when source_key in ('walk-in', 'walkin')                               then 'walk_in'
    end                                     as channel,
    cast(created_at as timestamp)           as created_at,
    cast(converted_customer_id as integer)  as converted_customer_id
from src

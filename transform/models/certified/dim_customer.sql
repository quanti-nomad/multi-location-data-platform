-- One row per real person: duplicates merged, test accounts removed.
with ids as (
    select * from {{ ref('int_customer_identity') }} where not is_test_account
),

customers as (
    select c.*, i.master_customer_id
    from {{ ref('stg_crm__customers') }} c
    join ids i using (customer_id)
)

select
    master_customer_id                                              as customer_id,
    min(created_at)                                                 as first_seen_at,
    arg_min(home_location_id, customer_id)                          as home_location_id,
    count(*)                                                        as source_records_merged
from customers
group by master_customer_id

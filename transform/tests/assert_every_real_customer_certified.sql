-- Every non-test source record must land in exactly one certified customer.
with src as (select count(*) as n from {{ ref('stg_crm__customers') }} where not is_test_account),
cert as (select sum(source_records_merged) as n from {{ ref('dim_customer') }})
select s.n as source_records, c.n as certified_records
from src s cross join cert c
where s.n <> c.n

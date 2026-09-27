-- Each normalized email belongs to exactly one certified customer.
select c.email_normalized, count(distinct i.master_customer_id) as masters
from {{ ref('stg_crm__customers') }} c
join {{ ref('int_customer_identity') }} i using (customer_id)
where c.email_normalized is not null and not c.is_test_account
group by 1
having count(distinct i.master_customer_id) > 1

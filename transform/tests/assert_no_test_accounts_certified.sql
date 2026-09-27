-- No test account may appear anywhere in the certified layer.
select p.payment_id
from {{ ref('fct_payments') }} p
join {{ ref('stg_crm__customers') }} c on c.customer_id = p.customer_id
where c.is_test_account

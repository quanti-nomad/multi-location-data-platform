{# Generic test: the combination of columns is unique (no external package needed). #}
{% test dbt_utils_free_unique_combo(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}

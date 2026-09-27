{# Parse a text amount such as "$1,234.50", "-179.00" or "$-179.00" into integer cents. #}
{% macro to_cents(col) -%}
    cast(round(cast(replace(replace(trim({{ col }}), '$', ''), ',', '') as decimal(14, 2)) * 100) as bigint)
{%- endmacro %}

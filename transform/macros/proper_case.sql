{# Title-case each word: "salt lake city" -> "Salt Lake City". #}
{% macro proper_case(col) -%}
    array_to_string(list_transform(string_split(lower({{ col }}), ' '), w -> upper(w[1]) || w[2:]), ' ')
{%- endmacro %}

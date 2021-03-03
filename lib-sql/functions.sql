{% include('functions/utils.sql') %}
{% include('functions/normalization.sql') %}
{% include('functions/ranking.sql') %}
{% include('functions/importance.sql') %}
{% include('functions/address_lookup.sql') %}
{% include('functions/interpolation.sql') %}

{% if 'place' in db.tables %}
    {% include 'functions/place_triggers.sql' %}
{% endif %}

{% if 'placex' in db.tables %}
    {% include 'functions/placex_triggers.sql' %}
{% endif %}

{% if 'location_postcode' in db.tables %}
    {% include 'functions/postcode_triggers.sql' %}
{% endif %}

{% include('functions/partition-functions.sql') %}

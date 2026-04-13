-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

{% include('functions/utils.sql') %}
{% include('functions/ranking.sql') %}
{% include('functions/importance.sql') %}
{% include('functions/interpolation.sql') %}
{% include('functions/updates.sql') %}

{% if 'place' in db.tables %}
    {% include 'functions/place_triggers.sql' %}
{% endif %}

{% if 'placex' in db.tables %}
    {% include 'functions/placex_triggers.sql' %}
{% endif %}

{% if 'location_postcodes' in db.tables %}
    {% include 'functions/postcode_triggers.sql' %}
{% endif %}

{% include('functions/partition-functions.sql') %}
{% include('functions/associated_street_triggers.sql') %}

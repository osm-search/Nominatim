-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP SEQUENCE IF EXISTS seq_place;
CREATE SEQUENCE seq_place start 1;

{% include('tables/status.sql') %}
{% include('tables/nominatim_properties.sql') %}
{% include('tables/location_area.sql') %}
{% include('tables/tiger.sql') %}
{% include('tables/interpolation.sql') %}
{% include('tables/search_name.sql') %}
{% include('tables/addressline.sql') %}
{% include('tables/placex.sql') %}
{% include('tables/postcodes.sql') %}
{% include('tables/entrance.sql') %}
{% include('tables/import_reports.sql') %}
{% include('tables/importance_tables.sql') %}

-- osm2pgsql does not create indexes on the middle tables for Nominatim
-- Add one for lookup of associated street relations.
{% if db.middle_db_format == '1' %}
CREATE INDEX planet_osm_rels_parts_associated_idx ON planet_osm_rels USING gin(parts)
  {{db.tablespace.address_index}}
  WHERE tags @> ARRAY['associatedStreet'];
{% else %}
CREATE INDEX planet_osm_rels_relation_members_idx ON planet_osm_rels USING gin(planet_osm_member_ids(members, 'R'::character(1)))
  WITH (fastupdate=off)
  {{db.tablespace.address_index}};
{% endif %}

-- Needed for lookups if a node is part of an interpolation.
CREATE INDEX IF NOT EXISTS idx_place_interpolations
    ON place USING gist(geometry) {{db.tablespace.address_index}}
    WHERE osm_type = 'W' and address ? 'interpolation';

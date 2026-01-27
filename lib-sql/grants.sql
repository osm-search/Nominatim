-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.
--
-- Grant read-only access to the web user for all Nominatim tables.

-- Core tables
GRANT SELECT ON import_status TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON country_name TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON nominatim_properties TO "{{config.DATABASE_WEBUSER}}";

-- Location tables
GRANT SELECT ON location_property_tiger TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON location_property_osmline TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON location_area TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON location_postcodes TO "{{config.DATABASE_WEBUSER}}";

-- Search tables
{% if not db.reverse_only %}
GRANT SELECT ON search_name TO "{{config.DATABASE_WEBUSER}}";
{% endif %}

-- Main place tables
GRANT SELECT ON placex TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON place_addressline TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON placex_entrance TO "{{config.DATABASE_WEBUSER}}";

-- OSM data tables
GRANT SELECT ON planet_osm_ways TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON planet_osm_rels TO "{{config.DATABASE_WEBUSER}}";

-- Error/delete tracking tables
GRANT SELECT ON import_polygon_error TO "{{config.DATABASE_WEBUSER}}";
GRANT SELECT ON import_polygon_delete TO "{{config.DATABASE_WEBUSER}}";

-- Country grid
GRANT SELECT ON country_osm_grid TO "{{config.DATABASE_WEBUSER}}";

-- Tokenizer tables (word table)
{% if 'word' in db.tables %}
GRANT SELECT ON word TO "{{config.DATABASE_WEBUSER}}";
{% endif %}

-- Tiger import table (if exists)
{% if 'location_property_tiger_import' in db.tables %}
GRANT SELECT ON location_property_tiger_import TO "{{config.DATABASE_WEBUSER}}";
{% endif %}
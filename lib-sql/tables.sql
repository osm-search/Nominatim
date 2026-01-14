-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

drop table if exists import_status;
CREATE TABLE import_status (
  lastimportdate timestamp with time zone NOT NULL,
  sequence_id integer,
  indexed boolean
  );
GRANT SELECT ON import_status TO "{{config.DATABASE_WEBUSER}}" ;

drop table if exists import_osmosis_log;
CREATE TABLE import_osmosis_log (
  batchend timestamp,
  batchseq integer,
  batchsize bigint,
  starttime timestamp,
  endtime timestamp,
  event text
  );

GRANT SELECT ON TABLE country_name TO "{{config.DATABASE_WEBUSER}}";

DROP TABLE IF EXISTS nominatim_properties;
CREATE TABLE nominatim_properties (
    property TEXT NOT NULL,
    value TEXT
);
GRANT SELECT ON TABLE nominatim_properties TO "{{config.DATABASE_WEBUSER}}";

drop table IF EXISTS location_area CASCADE;
CREATE TABLE location_area (
  place_id BIGINT NOT NULL,
  keywords INTEGER[] NOT NULL,
  partition SMALLINT NOT NULL,
  rank_search SMALLINT NOT NULL,
  rank_address SMALLINT NOT NULL,
  country_code VARCHAR(2),
  isguess BOOL NOT NULL,
  postcode TEXT,
  centroid GEOMETRY(Point, 4326) NOT NULL,
  geometry GEOMETRY(Geometry, 4326) NOT NULL
  );

CREATE TABLE location_area_large () INHERITS (location_area);

DROP TABLE IF EXISTS location_area_country;
CREATE TABLE location_area_country (
  place_id BIGINT NOT NULL,
  country_code varchar(2) NOT NULL,
  geometry GEOMETRY(Geometry, 4326) NOT NULL
  ) {{db.tablespace.address_data}};
CREATE INDEX idx_location_area_country_geometry ON location_area_country USING GIST (geometry) {{db.tablespace.address_index}};


CREATE TABLE location_property_tiger (
  place_id BIGINT NOT NULL,
  parent_place_id BIGINT,
  startnumber INTEGER NOT NULL,
  endnumber INTEGER NOT NULL,
  step SMALLINT NOT NULL,
  partition SMALLINT NOT NULL,
  linegeo GEOMETRY NOT NULL,
  postcode TEXT);
GRANT SELECT ON location_property_tiger TO "{{config.DATABASE_WEBUSER}}";

drop table if exists location_property_osmline;
CREATE TABLE location_property_osmline (
    place_id BIGINT NOT NULL,
    osm_id BIGINT NOT NULL,
    parent_place_id BIGINT,
    geometry_sector INTEGER NOT NULL,
    indexed_date TIMESTAMP,
    startnumber INTEGER,
    endnumber INTEGER,
    step SMALLINT,
    partition SMALLINT NOT NULL,
    indexed_status SMALLINT NOT NULL,
    linegeo GEOMETRY NOT NULL,
    address HSTORE,
    token_info JSONB, -- custom column for tokenizer use only
    postcode TEXT,
    country_code VARCHAR(2)
  ){{db.tablespace.search_data}};
CREATE UNIQUE INDEX idx_osmline_place_id ON location_property_osmline USING BTREE (place_id) {{db.tablespace.search_index}};
CREATE INDEX idx_osmline_geometry_sector ON location_property_osmline USING BTREE (geometry_sector) {{db.tablespace.address_index}};
CREATE INDEX idx_osmline_linegeo ON location_property_osmline USING GIST (linegeo) {{db.tablespace.search_index}}
  WHERE startnumber is not null;
GRANT SELECT ON location_property_osmline TO "{{config.DATABASE_WEBUSER}}";

drop table IF EXISTS search_name;
{% if not db.reverse_only %}
CREATE TABLE search_name (
  place_id BIGINT NOT NULL,
  importance FLOAT NOT NULL,
  search_rank SMALLINT NOT NULL,
  address_rank SMALLINT NOT NULL,
  name_vector integer[] NOT NULL,
  nameaddress_vector integer[] NOT NULL,
  country_code varchar(2),
  centroid GEOMETRY(Geometry, 4326) NOT NULL
  ) {{db.tablespace.search_data}};
CREATE UNIQUE INDEX idx_search_name_place_id
  ON search_name USING BTREE (place_id) {{db.tablespace.search_index}};
GRANT SELECT ON search_name to "{{config.DATABASE_WEBUSER}}" ;
{% endif %}

drop table IF EXISTS place_addressline;
CREATE TABLE place_addressline (
  place_id BIGINT NOT NULL,
  address_place_id BIGINT NOT NULL,
  distance FLOAT NOT NULL,
  cached_rank_address SMALLINT NOT NULL,
  fromarea boolean NOT NULL,
  isaddress boolean NOT NULL
  ) {{db.tablespace.search_data}};
CREATE INDEX idx_place_addressline_place_id on place_addressline USING BTREE (place_id) {{db.tablespace.search_index}};

---------  PLACEX - storage for all indexed places -----------------

DROP TABLE IF EXISTS placex;
CREATE TABLE placex (
  place_id BIGINT NOT NULL,
  parent_place_id BIGINT,
  linked_place_id BIGINT,
  importance FLOAT,
  indexed_date TIMESTAMP,
  geometry_sector INTEGER NOT NULL,
  rank_address SMALLINT NOT NULL,
  rank_search SMALLINT NOT NULL,
  partition SMALLINT NOT NULL,
  indexed_status SMALLINT NOT NULL,
  LIKE place INCLUDING CONSTRAINTS,
  wikipedia TEXT, -- calculated wikipedia article name (language:title)
  token_info JSONB, -- custom column for tokenizer use only
  country_code varchar(2),
  housenumber TEXT,
  postcode TEXT,
  centroid GEOMETRY(Geometry, 4326) NOT NULL
  ) {{db.tablespace.search_data}};

CREATE UNIQUE INDEX idx_place_id ON placex USING BTREE (place_id) {{db.tablespace.search_index}};
{% for osm_type in ('N', 'W', 'R') %}
CREATE INDEX idx_placex_osmid_{{osm_type | lower}} ON placex
  USING BTREE (osm_id) {{db.tablespace.search_index}}
  WHERE osm_type = '{{osm_type}}';
{% endfor %}

-- Usage: - removing linkage status on update
--        - lookup linked places for /details
CREATE INDEX idx_placex_linked_place_id ON placex
  USING BTREE (linked_place_id) {{db.tablespace.address_index}}
  WHERE linked_place_id IS NOT NULL;

-- Usage: - check that admin boundaries do not overtake each other rank-wise
--        - check that place node in a admin boundary with the same address level
--        - boundary is not completely contained in a place area
--        - parenting of large-area or unparentable features
CREATE INDEX idx_placex_geometry_address_area_candidates ON placex
  USING gist (geometry) {{db.tablespace.address_index}}
  WHERE rank_address between 1 and 25
        and ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon');

-- Usage: - POI is within building with housenumber
CREATE INDEX idx_placex_geometry_buildings ON placex
  USING SPGIST (geometry) {{db.tablespace.address_index}}
  WHERE address is not null and rank_search = 30
        and ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon');

-- Usage: - linking of similar named places to boundaries
--        - linking of place nodes with same type to boundaries
CREATE INDEX idx_placex_geometry_placenode ON placex
  USING SPGIST (geometry) {{db.tablespace.address_index}}
  WHERE osm_type = 'N' and rank_search < 26 and class = 'place';

-- Usage: - is node part of a way?
--        - find parent of interpolation spatially
CREATE INDEX idx_placex_geometry_lower_rank_ways ON placex
  USING SPGIST (geometry) {{db.tablespace.address_index}}
  WHERE osm_type = 'W' and rank_search >= 26;

-- Usage: - linking place nodes by wikidata tag to boundaries
CREATE INDEX idx_placex_wikidata on placex
  USING BTREE ((extratags -> 'wikidata')) {{db.tablespace.address_index}}
  WHERE extratags ? 'wikidata' and class = 'place'
        and osm_type = 'N' and rank_search < 26;

-- The following two indexes function as a todo list for indexing.

CREATE INDEX idx_placex_rank_address_sector ON placex
  USING BTREE (rank_address, geometry_sector) {{db.tablespace.address_index}}
  WHERE indexed_status > 0;

CREATE INDEX idx_placex_rank_boundaries_sector ON placex
  USING BTREE (rank_search, geometry_sector) {{db.tablespace.address_index}}
  WHERE class = 'boundary' and type = 'administrative'
        and indexed_status > 0;


DROP SEQUENCE IF EXISTS seq_place;
CREATE SEQUENCE seq_place start 1;
GRANT SELECT on placex to "{{config.DATABASE_WEBUSER}}" ;
GRANT SELECT on place_addressline to "{{config.DATABASE_WEBUSER}}" ;
GRANT SELECT ON planet_osm_ways to "{{config.DATABASE_WEBUSER}}" ;
GRANT SELECT ON planet_osm_rels to "{{config.DATABASE_WEBUSER}}" ;
GRANT SELECT on location_area to "{{config.DATABASE_WEBUSER}}" ;

-- Table for synthetic postcodes.
DROP TABLE IF EXISTS location_postcodes;
CREATE TABLE location_postcodes (
  place_id BIGINT NOT NULL,
  parent_place_id BIGINT,
  osm_id BIGINT,
  rank_search SMALLINT NOT NULL,
  indexed_status SMALLINT NOT NULL,
  indexed_date TIMESTAMP,
  country_code varchar(2) NOT NULL,
  postcode TEXT NOT NULL,
  centroid GEOMETRY(Geometry, 4326) NOT NULL,
  geometry GEOMETRY(Geometry, 4326) NOT NULL
  );
CREATE UNIQUE INDEX idx_location_postcodes_id ON location_postcodes
  USING BTREE (place_id) {{db.tablespace.search_index}};
CREATE INDEX idx_location_postcodes_geometry ON location_postcodes
  USING GIST (geometry) {{db.tablespace.search_index}};
CREATE INDEX IF NOT EXISTS idx_location_postcodes_postcode
  ON location_postcodes USING BTREE (postcode, country_code)
  {{db.tablespace.search_index}};
CREATE INDEX IF NOT EXISTS idx_location_postcodes_osmid
  ON location_postcodes USING BTREE (osm_id) {{db.tablespace.search_index}};
GRANT SELECT ON location_postcodes TO "{{config.DATABASE_WEBUSER}}" ;

-- Table to store location of entrance nodes
DROP TABLE IF EXISTS placex_entrance;
CREATE TABLE placex_entrance (
  place_id BIGINT NOT NULL,
  osm_id BIGINT NOT NULL,
  type TEXT NOT NULL,
  location GEOMETRY(Point, 4326) NOT NULL,
  extratags HSTORE
  );
CREATE UNIQUE INDEX idx_placex_entrance_place_id_osm_id ON placex_entrance
  USING BTREE (place_id, osm_id) {{db.tablespace.search_index}};
GRANT SELECT ON placex_entrance TO "{{config.DATABASE_WEBUSER}}" ;

-- Create an index on the place table for lookups to populate the entrance
-- table
CREATE INDEX IF NOT EXISTS idx_placex_entrance_lookup ON place
  USING BTREE (osm_id)
  WHERE class IN ('routing:entrance', 'entrance');

DROP TABLE IF EXISTS import_polygon_error;
CREATE TABLE import_polygon_error (
  osm_id BIGINT,
  osm_type CHAR(1),
  class TEXT NOT NULL,
  type TEXT NOT NULL,
  name HSTORE,
  country_code varchar(2),
  updated timestamp,
  errormessage text,
  prevgeometry GEOMETRY(Geometry, 4326),
  newgeometry GEOMETRY(Geometry, 4326)
  );
CREATE INDEX idx_import_polygon_error_osmid ON import_polygon_error USING BTREE (osm_type, osm_id);
GRANT SELECT ON import_polygon_error TO "{{config.DATABASE_WEBUSER}}";

DROP TABLE IF EXISTS import_polygon_delete;
CREATE TABLE import_polygon_delete (
  osm_id BIGINT,
  osm_type CHAR(1),
  class TEXT NOT NULL,
  type TEXT NOT NULL
  );
CREATE INDEX idx_import_polygon_delete_osmid ON import_polygon_delete USING BTREE (osm_type, osm_id);
GRANT SELECT ON import_polygon_delete TO "{{config.DATABASE_WEBUSER}}";

DROP SEQUENCE IF EXISTS file;
CREATE SEQUENCE file start 1;

{% if 'wikimedia_importance' not in db.tables and 'wikipedia_article' not in db.tables %}
-- create dummy tables here, if nothing was imported
CREATE TABLE wikimedia_importance (
  language TEXT NOT NULL,
  title TEXT NOT NULL,
  importance double precision NOT NULL,
  wikidata TEXT
)  {{db.tablespace.address_data}};
{% endif %}

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

GRANT SELECT ON table country_osm_grid to "{{config.DATABASE_WEBUSER}}";

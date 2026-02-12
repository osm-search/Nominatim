-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

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
CREATE INDEX IF NOT EXISTS idx_location_postcodes_postcode ON location_postcodes
  USING BTREE (postcode, country_code) {{db.tablespace.search_index}};
CREATE INDEX IF NOT EXISTS idx_location_postcodes_osmid ON location_postcodes
  USING BTREE (osm_id) {{db.tablespace.search_index}};


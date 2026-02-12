-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP TABLE IF EXISTS location_area CASCADE;
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

CREATE INDEX idx_location_area_country_geometry ON location_area_country
  USING GIST (geometry) {{db.tablespace.address_index}};

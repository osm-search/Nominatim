-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

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

CREATE INDEX idx_import_polygon_error_osmid ON import_polygon_error
  USING BTREE (osm_type, osm_id);


DROP TABLE IF EXISTS import_polygon_delete;
CREATE TABLE import_polygon_delete (
  osm_id BIGINT,
  osm_type CHAR(1),
  class TEXT NOT NULL,
  type TEXT NOT NULL
  );

CREATE INDEX idx_import_polygon_delete_osmid ON import_polygon_delete
  USING BTREE (osm_type, osm_id);

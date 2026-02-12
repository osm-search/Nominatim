-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

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

-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP TABLE IF EXISTS location_property_osmline;
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

CREATE UNIQUE INDEX idx_osmline_place_id ON location_property_osmline
  USING BTREE (place_id) {{db.tablespace.search_index}};
CREATE INDEX idx_osmline_geometry_sector ON location_property_osmline
  USING BTREE (geometry_sector) {{db.tablespace.address_index}};
CREATE INDEX idx_osmline_linegeo ON location_property_osmline
  USING GIST (linegeo) {{db.tablespace.search_index}}
  WHERE startnumber is not null;


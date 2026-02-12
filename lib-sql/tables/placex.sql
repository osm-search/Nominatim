-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- placex - main table for searchable places

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


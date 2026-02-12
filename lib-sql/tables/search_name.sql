-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP TABLE IF EXISTS search_name;

{% if not create_reverse_only %}

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

{% endif %}

-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

drop table IF EXISTS search_name_blank CASCADE;
CREATE TABLE search_name_blank (
  place_id BIGINT,
  address_rank smallint,
  name_vector integer[],
  centroid GEOMETRY(Geometry, 4326)
  );


{% for partition in db.partitions %}
  CREATE TABLE location_area_large_{{ partition }} () INHERITS (location_area_large) {{db.tablespace.address_data}};
  CREATE INDEX idx_location_area_large_{{ partition }}_place_id ON location_area_large_{{ partition }} USING BTREE (place_id) {{db.tablespace.address_index}};
  CREATE INDEX idx_location_area_large_{{ partition }}_geometry ON location_area_large_{{ partition }} USING GIST (geometry) {{db.tablespace.address_index}};

  CREATE TABLE search_name_{{ partition }} () INHERITS (search_name_blank) {{db.tablespace.address_data}};
  CREATE INDEX idx_search_name_{{ partition }}_place_id ON search_name_{{ partition }} USING BTREE (place_id) {{db.tablespace.address_index}};
  CREATE INDEX idx_search_name_{{ partition }}_centroid_street ON search_name_{{ partition }} USING GIST (centroid) {{db.tablespace.address_index}} where address_rank between 26 and 27;
  CREATE INDEX idx_search_name_{{ partition }}_centroid_place ON search_name_{{ partition }} USING GIST (centroid) {{db.tablespace.address_index}} where address_rank between 2 and 25;

  DROP TABLE IF EXISTS location_road_{{ partition }};
  CREATE TABLE location_road_{{ partition }} (
    place_id BIGINT,
    partition SMALLINT,
    country_code VARCHAR(2),
    geometry GEOMETRY(Geometry, 4326)
    ) {{db.tablespace.address_data}};
  CREATE INDEX idx_location_road_{{ partition }}_geometry ON location_road_{{ partition }} USING GIST (geometry) {{db.tablespace.address_index}};
  CREATE INDEX idx_location_road_{{ partition }}_place_id ON location_road_{{ partition }} USING BTREE (place_id) {{db.tablespace.address_index}};

{% endfor %}

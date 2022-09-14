-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Indices used only during search and update.
-- These indices are created only after the indexing process is done.

CREATE INDEX IF NOT EXISTS idx_place_addressline_address_place_id
  ON place_addressline USING BTREE (address_place_id) {{db.tablespace.search_index}};
---
CREATE INDEX IF NOT EXISTS idx_placex_rank_search
  ON placex USING BTREE (rank_search) {{db.tablespace.search_index}};
---
CREATE INDEX IF NOT EXISTS idx_placex_rank_address
  ON placex USING BTREE (rank_address) {{db.tablespace.search_index}};
---
CREATE INDEX IF NOT EXISTS idx_placex_parent_place_id
  ON placex USING BTREE (parent_place_id) {{db.tablespace.search_index}}
  WHERE parent_place_id IS NOT NULL;
---
CREATE INDEX IF NOT EXISTS idx_placex_geometry_reverse_lookupPolygon
  ON placex USING gist (geometry) {{db.tablespace.search_index}}
  WHERE St_GeometryType(geometry) in ('ST_Polygon', 'ST_MultiPolygon')
    AND rank_address between 4 and 25 AND type != 'postcode'
    AND name is not null AND indexed_status = 0 AND linked_place_id is null;
---
CREATE INDEX IF NOT EXISTS idx_osmline_parent_place_id
  ON location_property_osmline USING BTREE (parent_place_id) {{db.tablespace.search_index}}
  WHERE parent_place_id is not null;
---
CREATE INDEX IF NOT EXISTS idx_osmline_parent_osm_id
  ON location_property_osmline USING BTREE (osm_id) {{db.tablespace.search_index}};
---
CREATE INDEX IF NOT EXISTS idx_postcode_postcode
  ON location_postcode USING BTREE (postcode) {{db.tablespace.search_index}};
-- Indices only needed for updating.

{% if not drop %}
---
  CREATE INDEX IF NOT EXISTS idx_placex_pendingsector
    ON placex USING BTREE (rank_address,geometry_sector) {{db.tablespace.address_index}}
    WHERE indexed_status > 0;
---
  CREATE INDEX IF NOT EXISTS idx_location_area_country_place_id
    ON location_area_country USING BTREE (place_id) {{db.tablespace.address_index}};
---
  CREATE UNIQUE INDEX IF NOT EXISTS idx_place_osm_unique
    ON place USING btree(osm_id, osm_type, class, type) {{db.tablespace.address_index}};
{% endif %}

-- Indices only needed for search.
{% if 'search_name' in db.tables %}
---
  CREATE INDEX IF NOT EXISTS idx_search_name_nameaddress_vector
    ON search_name USING GIN (nameaddress_vector) WITH (fastupdate = off) {{db.tablespace.search_index}};
---
  CREATE INDEX IF NOT EXISTS idx_search_name_name_vector
    ON search_name USING GIN (name_vector) WITH (fastupdate = off) {{db.tablespace.search_index}};
---
  CREATE INDEX IF NOT EXISTS idx_search_name_centroid
    ON search_name USING GIST (centroid) {{db.tablespace.search_index}};

  {% if postgres.has_index_non_key_column %}
---
    CREATE INDEX IF NOT EXISTS idx_placex_housenumber
      ON placex USING btree (parent_place_id)
      INCLUDE (housenumber) {{db.tablespace.search_index}}
      WHERE housenumber is not null;
---
    CREATE INDEX IF NOT EXISTS idx_osmline_parent_osm_id_with_hnr
      ON location_property_osmline USING btree(parent_place_id)
      INCLUDE (startnumber, endnumber) {{db.tablespace.search_index}}
      WHERE startnumber is not null;
  {% endif %}
{% endif %}

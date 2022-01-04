-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

--index only on parent_place_id
CREATE INDEX IF NOT EXISTS idx_location_property_tiger_parent_place_id_imp
  ON location_property_tiger_import (parent_place_id)
{% if postgres.has_index_non_key_column %}
  INCLUDE (startnumber, endnumber)
{% endif %}
  {{db.tablespace.aux_index}};
CREATE UNIQUE INDEX IF NOT EXISTS idx_location_property_tiger_place_id_imp
  ON location_property_tiger_import (place_id) {{db.tablespace.aux_index}};

GRANT SELECT ON location_property_tiger_import TO "{{config.DATABASE_WEBUSER}}";

DROP TABLE IF EXISTS location_property_tiger;
ALTER TABLE location_property_tiger_import RENAME TO location_property_tiger;

ALTER INDEX IF EXISTS idx_location_property_tiger_parent_place_id_imp RENAME TO idx_location_property_tiger_housenumber_parent_place_id;
ALTER INDEX IF EXISTS idx_location_property_tiger_place_id_imp RENAME TO idx_location_property_tiger_place_id;

DROP FUNCTION tiger_line_import (linegeo GEOMETRY, in_startnumber INTEGER,
                                 in_endnumber INTEGER, interpolationtype TEXT,
                                 token_info JSONB, in_postcode TEXT);

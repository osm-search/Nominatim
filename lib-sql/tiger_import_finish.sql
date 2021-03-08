--index only on parent_place_id
CREATE INDEX {{sql.if_index_not_exists}} idx_location_property_tiger_place_id_imp
  ON location_property_tiger_import (parent_place_id) {{db.tablespace.aux_index}};
CREATE UNIQUE INDEX {{sql.if_index_not_exists}} idx_location_property_tiger_place_id_imp
  ON location_property_tiger_import (place_id) {{db.tablespace.aux_index}};

GRANT SELECT ON location_property_tiger_import TO "{{config.DATABASE_WEBUSER}}";

DROP TABLE IF EXISTS location_property_tiger;
ALTER TABLE location_property_tiger_import RENAME TO location_property_tiger;

ALTER INDEX IF EXISTS idx_location_property_tiger_parent_place_id_imp RENAME TO idx_location_property_tiger_housenumber_parent_place_id;
ALTER INDEX IF EXISTS idx_location_property_tiger_place_id_imp RENAME TO idx_location_property_tiger_place_id;

DROP FUNCTION tiger_line_import (linegeo geometry, in_startnumber integer, in_endnumber integer, interpolationtype text, in_street text, in_isin text, in_postcode text);

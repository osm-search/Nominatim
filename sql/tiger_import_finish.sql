CREATE INDEX idx_location_property_tiger_housenumber_parent_place_id_imp ON location_property_tiger_import (parent_place_id, housenumber) {ts:aux-index};
CREATE UNIQUE INDEX idx_location_property_tiger_place_id_imp ON location_property_tiger_import (place_id) {ts:aux-index};

GRANT SELECT ON location_property_tiger_import TO "{www-user}";

DROP TABLE IF EXISTS location_property_tiger;
ALTER TABLE location_property_tiger_import RENAME TO location_property_tiger;

ALTER INDEX idx_location_property_tiger_housenumber_parent_place_id_imp RENAME TO idx_location_property_tiger_housenumber_parent_place_id;
ALTER INDEX idx_location_property_tiger_place_id_imp RENAME TO idx_location_property_tiger_place_id;

DROP FUNCTION tigger_create_interpolation (linegeo geometry, in_startnumber integer, in_endnumber integer, interpolationtype text, in_street text, in_isin text, in_postcode text);

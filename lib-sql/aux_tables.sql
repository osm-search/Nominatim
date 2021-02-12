CREATE TABLE location_property_aux () INHERITS (location_property);
CREATE INDEX idx_location_property_aux_place_id ON location_property_aux USING BTREE (place_id);
CREATE INDEX idx_location_property_aux_parent_place_id ON location_property_aux USING BTREE (parent_place_id);
CREATE INDEX idx_location_property_aux_housenumber_parent_place_id ON location_property_aux USING BTREE (parent_place_id, housenumber);
GRANT SELECT ON location_property_aux TO "{www-user}";


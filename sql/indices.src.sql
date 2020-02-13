-- Indices used only during search and update.
-- These indices are created only after the indexing process is done.

CREATE INDEX CONCURRENTLY idx_word_word_id on word USING BTREE (word_id) {ts:search-index};

CREATE INDEX CONCURRENTLY idx_place_addressline_address_place_id on place_addressline USING BTREE (address_place_id) {ts:search-index};

DROP INDEX CONCURRENTLY IF EXISTS idx_placex_rank_search;
CREATE INDEX CONCURRENTLY idx_placex_rank_search ON placex USING BTREE (rank_search) {ts:search-index};
CREATE INDEX CONCURRENTLY idx_placex_rank_address ON placex USING BTREE (rank_address) {ts:search-index};
CREATE INDEX CONCURRENTLY idx_placex_parent_place_id ON placex USING BTREE (parent_place_id) {ts:search-index} where parent_place_id IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_placex_geometry_reverse_lookupPoint
  ON placex USING gist (geometry) {ts:search-index}
  WHERE (name is not null or housenumber is not null or rank_address between 26 and 27)
    AND class not in ('railway','tunnel','bridge','man_made')
    AND rank_address >= 26 AND indexed_status = 0 AND linked_place_id is null;
CREATE INDEX CONCURRENTLY idx_placex_geometry_reverse_lookupPolygon
  ON placex USING gist (geometry) {ts:search-index}
  WHERE St_GeometryType(geometry) in ('ST_Polygon', 'ST_MultiPolygon')
    AND rank_address between 4 and 25 AND type != 'postcode'
    AND name is not null AND indexed_status = 0 AND linked_place_id is null;
CREATE INDEX CONCURRENTLY idx_placex_geometry_reverse_placeNode
  ON placex USING gist (geometry) {ts:search-index}
  WHERE osm_type = 'N' AND rank_search between 5 and 25
    AND class = 'place' AND type != 'postcode'
    AND name is not null AND indexed_status = 0 AND linked_place_id is null;

GRANT SELECT ON table country_osm_grid to "{www-user}";

CREATE INDEX CONCURRENTLY idx_osmline_parent_place_id ON location_property_osmline USING BTREE (parent_place_id) {ts:search-index};
CREATE INDEX CONCURRENTLY idx_osmline_parent_osm_id ON location_property_osmline USING BTREE (osm_id) {ts:search-index};

CREATE UNIQUE INDEX CONCURRENTLY idx_postcode_id ON location_postcode USING BTREE (place_id) {ts:search-index};
CREATE INDEX CONCURRENTLY idx_postcode_postcode ON location_postcode USING BTREE (postcode) {ts:search-index};

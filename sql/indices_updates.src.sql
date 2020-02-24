-- Indices used only during search and update.
-- These indices are created only after the indexing process is done.

CREATE INDEX CONCURRENTLY idx_placex_pendingsector ON placex USING BTREE (rank_search,geometry_sector) {ts:address-index} where indexed_status > 0;

CREATE INDEX CONCURRENTLY idx_location_area_country_place_id ON location_area_country USING BTREE (place_id) {ts:address-index};

DROP INDEX CONCURRENTLY IF EXISTS place_id_idx;
CREATE UNIQUE INDEX CONCURRENTLY idx_place_osm_unique on place using btree(osm_id,osm_type,class,type) {ts:address-index};

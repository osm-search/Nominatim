-- Indices used only during search and update.
-- These indices are created only after the indexing process is done.

CREATE INDEX idx_word_word_id on word USING BTREE (word_id) {ts:search-index};

CREATE INDEX idx_search_name_nameaddress_vector ON search_name USING GIN (nameaddress_vector) WITH (fastupdate = off) {ts:search-index};
CREATE INDEX idx_search_name_name_vector ON search_name USING GIN (name_vector) WITH (fastupdate = off) {ts:search-index};
CREATE INDEX idx_search_name_centroid ON search_name USING GIST (centroid) {ts:search-index};

CREATE INDEX idx_place_addressline_address_place_id on place_addressline USING BTREE (address_place_id) {ts:search-index};

DROP INDEX IF EXISTS idx_placex_rank_search;
CREATE INDEX idx_placex_rank_search ON placex USING BTREE (rank_search) {ts:search-index};
CREATE INDEX idx_placex_rank_address ON placex USING BTREE (rank_address) {ts:search-index};
CREATE INDEX idx_placex_pendingsector ON placex USING BTREE (rank_search,geometry_sector) {ts:address-index} where indexed_status > 0;
CREATE INDEX idx_placex_parent_place_id ON placex USING BTREE (parent_place_id) {ts:search-index} where parent_place_id IS NOT NULL;
CREATE INDEX idx_placex_reverse_geometry ON placex USING gist (geometry) {ts:search-index} where rank_search != 28 and (name is not null or housenumber is not null) and class not in ('waterway','railway','tunnel','bridge','man_made');
CREATE INDEX idx_location_area_country_place_id ON location_area_country USING BTREE (place_id) {ts:address-index};

CREATE INDEX idx_osmline_parent_place_id ON location_property_osmline USING BTREE (parent_place_id) {ts:search-index};

CREATE INDEX idx_search_name_country_centroid ON search_name_country USING GIST (centroid) {ts:address-index};

DROP INDEX IF EXISTS place_id_idx;
CREATE UNIQUE INDEX idx_place_osm_unique on place using btree(osm_id,osm_type,class,type) {ts:address-index};


CREATE UNIQUE INDEX idx_postcode_id ON location_postcode USING BTREE (place_id) {ts:search-index};
CREATE INDEX idx_postcode_postcode ON location_postcode USING BTREE (postcode) {ts:search-index};

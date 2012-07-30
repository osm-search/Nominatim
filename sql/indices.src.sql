-- Indices used only during search and update.
-- These indices are created only after the indexing process is done.

CREATE INDEX idx_word_word_id on word USING BTREE (word_id);

CREATE INDEX idx_search_name_nameaddress_vector ON search_name USING GIN (nameaddress_vector) WITH (fastupdate = off);
CREATE INDEX idx_search_name_name_vector ON search_name USING GIN (name_vector) WITH (fastupdate = off);
CREATE INDEX idx_search_name_centroid ON search_name USING GIST (centroid);

CREATE INDEX idx_place_addressline_address_place_id on place_addressline USING BTREE (address_place_id);

CREATE INDEX idx_place_boundingbox_place_id on place_boundingbox USING BTREE (place_id);
CREATE INDEX idx_place_boundingbox_outline ON place_boundingbox USING GIST (outline);

DROP INDEX IF EXISTS idx_placex_rank_search;
CREATE INDEX idx_placex_rank_search ON placex USING BTREE (rank_search);
CREATE INDEX idx_placex_rank_address ON placex USING BTREE (rank_address);
CREATE INDEX idx_placex_pendingsector ON placex USING BTREE (rank_search,geometry_sector) where indexed_status > 0;
CREATE INDEX idx_placex_parent_place_id ON placex USING BTREE (parent_place_id) where parent_place_id IS NOT NULL;
CREATE INDEX idx_placex_interpolation ON placex USING BTREE (geometry_sector) where indexed_status > 0 and class='place' and type='houses';
CREATE INDEX idx_location_area_country_place_id ON location_area_country USING BTREE (place_id);

CREATE INDEX idx_search_name_country_centroid ON search_name_country USING GIST (centroid);
CREATE INDEX idx_search_name_country_nameaddress_vector ON search_name_country USING GIN (nameaddress_vector) WITH (fastupdate = off);

-- start
CREATE INDEX idx_location_property_-partition-_centroid ON location_property_-partition- USING GIST (centroid);
-- end

CREATE UNIQUE INDEX idx_place_osm_unique on place using btree(osm_id,osm_type,class,type);

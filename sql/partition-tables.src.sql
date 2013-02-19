drop type nearplace cascade;
create type nearplace as (
  place_id BIGINT
);

drop type nearfeature cascade;
create type nearfeature as (
  place_id BIGINT,
  keywords int[],
  rank_address integer,
  rank_search integer,
  distance float,
  isguess boolean
);

drop type nearfeaturecentr cascade;
create type nearfeaturecentr as (
  place_id BIGINT,
  keywords int[],
  rank_address integer,
  rank_search integer,
  distance float,
  isguess boolean,
  centroid GEOMETRY
);

drop table IF EXISTS search_name_blank CASCADE;
CREATE TABLE search_name_blank (
  place_id BIGINT,
  search_rank integer,
  address_rank integer,
  name_vector integer[]
  );
SELECT AddGeometryColumn('search_name_blank', 'centroid', 4326, 'GEOMETRY', 2);


CREATE TABLE location_area_country () INHERITS (location_area_large);
CREATE INDEX idx_location_area_country_geometry ON location_area_country USING GIST (geometry);

CREATE TABLE search_name_country () INHERITS (search_name_blank);
CREATE INDEX idx_search_name_country_place_id ON search_name_country USING BTREE (place_id);
CREATE INDEX idx_search_name_country_name_vector ON search_name_country USING GIN (name_vector) WITH (fastupdate = off);

-- start
CREATE TABLE location_area_large_-partition- () INHERITS (location_area_large);
CREATE INDEX idx_location_area_large_-partition-_place_id ON location_area_large_-partition- USING BTREE (place_id);
CREATE INDEX idx_location_area_large_-partition-_geometry ON location_area_large_-partition- USING GIST (geometry);

CREATE TABLE search_name_-partition- () INHERITS (search_name_blank);
CREATE INDEX idx_search_name_-partition-_place_id ON search_name_-partition- USING BTREE (place_id);
CREATE INDEX idx_search_name_-partition-_centroid ON search_name_-partition- USING GIST (centroid);
CREATE INDEX idx_search_name_-partition-_name_vector ON search_name_-partition- USING GIN (name_vector) WITH (fastupdate = off);

CREATE TABLE location_property_-partition- () INHERITS (location_property);
CREATE INDEX idx_location_property_-partition-_place_id ON location_property_-partition- USING BTREE (place_id);
CREATE INDEX idx_location_property_-partition-_parent_place_id ON location_property_-partition- USING BTREE (parent_place_id);
CREATE INDEX idx_location_property_-partition-_housenumber_parent_place_id ON location_property_-partition- USING BTREE (parent_place_id, housenumber);

CREATE TABLE location_road_-partition- (
  partition integer,
  place_id BIGINT,
  country_code VARCHAR(2)
  );
SELECT AddGeometryColumn('location_road_-partition-', 'geometry', 4326, 'GEOMETRY', 2);
CREATE INDEX idx_location_road_-partition-_geometry ON location_road_-partition- USING GIST (geometry);
CREATE INDEX idx_location_road_-partition-_place_id ON location_road_-partition- USING BTREE (place_id);

-- end

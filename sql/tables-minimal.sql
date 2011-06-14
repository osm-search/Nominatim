drop table import_npi_log;
CREATE TABLE import_npi_log (
  npiid integer,
  batchend timestamp,
  batchsize integer,
  starttime timestamp,
  endtime timestamp,
  event text
  );

drop table IF EXISTS word;
CREATE TABLE word (
  word_id INTEGER,
  word_token text,
  word_trigram text,
  word text,
  class text,
  type text,
  country_code varchar(2),
  search_name_count INTEGER,
  operator TEXT
  );
SELECT AddGeometryColumn('word', 'location', 4326, 'GEOMETRY', 2);
CREATE INDEX idx_word_word_id on word USING BTREE (word_id);
CREATE INDEX idx_word_word_token on word USING BTREE (word_token);
GRANT SELECT ON word TO "www-data" ;
DROP SEQUENCE seq_word;
CREATE SEQUENCE seq_word start 1;

drop table IF EXISTS location_property CASCADE;
CREATE TABLE location_property (
  place_id BIGINT,
  partition integer,
  parent_place_id BIINT,
  housenumber TEXT,
  postcode TEXT
  );
SELECT AddGeometryColumn('location_property', 'centroid', 4326, 'POINT', 2);

CREATE TABLE location_property_aux () INHERITS (location_property);
CREATE INDEX idx_location_property_aux_place_id ON location_property_aux USING BTREE (place_id);
CREATE INDEX idx_location_property_aux_parent_place_id ON location_property_aux USING BTREE (parent_place_id);
CREATE INDEX idx_location_property_aux_housenumber_parent_place_id ON location_property_aux USING BTREE (parent_place_id, housenumber);

CREATE TABLE location_property_tiger () INHERITS (location_property);
CREATE INDEX idx_location_property_tiger_place_id ON location_property_tiger USING BTREE (place_id);
CREATE INDEX idx_location_property_tiger_parent_place_id ON location_property_tiger USING BTREE (parent_place_id);
CREATE INDEX idx_location_property_tiger_housenumber_parent_place_id ON location_property_tiger USING BTREE (parent_place_id, housenumber);

drop table IF EXISTS search_name_blank CASCADE;
CREATE TABLE search_name_blank (
  place_id BIGINT,
  search_rank integer,
  address_rank integer,
  importance FLOAT,
  country_code varchar(2),
  name_vector integer[],
  nameaddress_vector integer[]
  );
SELECT AddGeometryColumn('search_name_blank', 'centroid', 4326, 'GEOMETRY', 2);

drop table IF EXISTS search_name;
CREATE TABLE search_name () INHERITS (search_name_blank);
CREATE INDEX search_name_name_vector_idx ON search_name USING GIN (name_vector gin__int_ops) WITH (fastupdate = off);
CREATE INDEX searchnameplacesearch_search_nameaddress_vector_idx ON search_name USING GIN (nameaddress_vector gin__int_ops) WITH (fastupdate = off);
CREATE INDEX idx_search_name_centroid ON search_name USING GIST (centroid);
CREATE INDEX idx_search_name_place_id ON search_name USING BTREE (place_id);

drop table IF EXISTS place_addressline;
CREATE TABLE place_addressline (
  place_id BIGINT,
  address_place_id BIGINT,
  fromarea boolean,
  isaddress boolean,
  distance float,
  cached_rank_address integer
  );
CREATE INDEX idx_place_addressline_place_id on place_addressline USING BTREE (place_id);
CREATE INDEX idx_place_addressline_address_place_id on place_addressline USING BTREE (address_place_id);

drop table IF EXISTS place_boundingbox CASCADE;
CREATE TABLE place_boundingbox (
  place_id BIGINT,
  minlat float,
  maxlat float,
  minlon float,
  maxlon float,
  numfeatures integer,
  area float
  );
CREATE INDEX idx_place_boundingbox_place_id on place_boundingbox USING BTREE (place_id);
SELECT AddGeometryColumn('place_boundingbox', 'outline', 4326, 'GEOMETRY', 2);
CREATE INDEX idx_place_boundingbox_outline ON place_boundingbox USING GIST (outline);
GRANT SELECT on place_boundingbox to "www-data" ;
GRANT INSERT on place_boundingbox to "www-data" ;

drop table country;
CREATE TABLE country (
  country_code varchar(2),
  country_name hstore,
  country_default_language_code varchar(2)
  );
SELECT AddGeometryColumn('country', 'geometry', 4326, 'POLYGON', 2);
insert into country select iso3166::varchar(2), 'name:en'->cntry_name, null, 
  ST_Transform(geometryn(the_geom, generate_series(1, numgeometries(the_geom))), 4326) from worldboundaries;
CREATE INDEX idx_country_country_code ON country USING BTREE (country_code);
CREATE INDEX idx_country_geometry ON country USING GIST (geometry);

drop table placex;
CREATE TABLE placex (
  place_id BIGINT NOT NULL,
  partition integer,
  osm_type char(1),
  osm_id INTEGER,
  class TEXT NOT NULL,
  type TEXT NOT NULL,
  name HSTORE,
  admin_level INTEGER,
  housenumber TEXT,
  street TEXT,
  isin TEXT,
  postcode TEXT,
  country_code varchar(2),
  extratags HSTORE,
  parent_place_id BIGINT,
  linked_place_id BIGINT,
  rank_address INTEGER,
  rank_search INTEGER,
  importance FLOAT,
  indexed_status INTEGER,
  indexed_date TIMESTAMP,
  geometry_sector INTEGER
  );
SELECT AddGeometryColumn('placex', 'geometry', 4326, 'GEOMETRY', 2);
CREATE UNIQUE INDEX idx_place_id ON placex USING BTREE (place_id);
CREATE INDEX idx_placex_osmid ON placex USING BTREE (osm_type, osm_id);
CREATE INDEX idx_placex_rank_search ON placex USING BTREE (rank_search);
CREATE INDEX idx_placex_rank_address ON placex USING BTREE (rank_address);
CREATE INDEX idx_placex_geometry ON placex USING GIST (geometry);
CREATE INDEX idx_placex_parent_place_id ON placex USING BTREE (parent_place_id) where parent_place_id IS NOT NULL;

DROP SEQUENCE seq_place;
CREATE SEQUENCE seq_place start 1;
GRANT SELECT on placex to "www-data" ;
GRANT UPDATE ON placex to "www-data" ;
GRANT SELECT ON search_name to "www-data" ;
GRANT DELETE on search_name to "www-data" ;
GRANT INSERT on search_name to "www-data" ;
GRANT SELECT on place_addressline to "www-data" ;
GRANT INSERT ON place_addressline to "www-data" ;
GRANT DELETE on place_addressline to "www-data" ;
GRANT SELECT ON seq_word to "www-data" ;
GRANT UPDATE ON seq_word to "www-data" ;
GRANT INSERT ON word to "www-data" ;
GRANT SELECT on country to "www-data" ;

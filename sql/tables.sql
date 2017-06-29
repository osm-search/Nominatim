drop table if exists import_status;
CREATE TABLE import_status (
  lastimportdate timestamp NOT NULL,
  sequence_id integer,
  indexed boolean
  );
GRANT SELECT ON import_status TO "{www-user}" ;

drop table if exists import_osmosis_log;
CREATE TABLE import_osmosis_log (
  batchend timestamp,
  batchseq integer,
  batchsize integer,
  starttime timestamp,
  endtime timestamp,
  event text
  );

CREATE TABLE new_query_log (
  type text,
  starttime timestamp,
  ipaddress text,
  useragent text,
  language text,
  query text,
  searchterm text,
  endtime timestamp,
  results integer,
  format text,
  secret text
  );
CREATE INDEX idx_new_query_log_starttime ON new_query_log USING BTREE (starttime);
GRANT INSERT ON new_query_log TO "{www-user}" ;
GRANT UPDATE ON new_query_log TO "{www-user}" ;
GRANT SELECT ON new_query_log TO "{www-user}" ;

GRANT SELECT ON TABLE country_name TO "{www-user}";
GRANT SELECT ON TABLE gb_postcode TO "{www-user}";

drop table IF EXISTS word;
CREATE TABLE word (
  word_id INTEGER,
  word_token text,
  word text,
  class text,
  type text,
  country_code varchar(2),
  search_name_count INTEGER,
  operator TEXT
  ) {ts:search-data};
CREATE INDEX idx_word_word_token on word USING BTREE (word_token) {ts:search-index};
GRANT SELECT ON word TO "{www-user}" ;
DROP SEQUENCE IF EXISTS seq_word;
CREATE SEQUENCE seq_word start 1;

drop table IF EXISTS location_area CASCADE;
CREATE TABLE location_area (
  place_id BIGINT,
  keywords INTEGER[],
  partition SMALLINT,
  rank_search SMALLINT NOT NULL,
  rank_address SMALLINT NOT NULL,
  country_code VARCHAR(2),
  isguess BOOL
  );
SELECT AddGeometryColumn('location_area', 'centroid', 4326, 'POINT', 2);
SELECT AddGeometryColumn('location_area', 'geometry', 4326, 'GEOMETRY', 2);

CREATE TABLE location_area_large () INHERITS (location_area);

drop table IF EXISTS location_property CASCADE;
CREATE TABLE location_property (
  place_id BIGINT,
  parent_place_id BIGINT,
  partition SMALLINT,
  housenumber TEXT,
  postcode TEXT
  );
SELECT AddGeometryColumn('location_property', 'centroid', 4326, 'POINT', 2);

CREATE TABLE location_property_aux () INHERITS (location_property);
CREATE INDEX idx_location_property_aux_place_id ON location_property_aux USING BTREE (place_id);
CREATE INDEX idx_location_property_aux_parent_place_id ON location_property_aux USING BTREE (parent_place_id);
CREATE INDEX idx_location_property_aux_housenumber_parent_place_id ON location_property_aux USING BTREE (parent_place_id, housenumber);
GRANT SELECT ON location_property_aux TO "{www-user}";

CREATE TABLE location_property_tiger (
  place_id BIGINT,
  parent_place_id BIGINT,
  startnumber INTEGER,
  endnumber INTEGER,
  partition SMALLINT,
  linegeo GEOMETRY,
  interpolationtype TEXT,
  postcode TEXT);
GRANT SELECT ON location_property_tiger TO "{www-user}";

drop table if exists location_property_osmline;
CREATE TABLE location_property_osmline (
    place_id BIGINT NOT NULL,
    osm_id BIGINT,
    parent_place_id BIGINT,
    geometry_sector INTEGER,
    indexed_date TIMESTAMP,
    startnumber INTEGER,
    endnumber INTEGER,
    partition SMALLINT,
    indexed_status SMALLINT,
    linegeo GEOMETRY,
    interpolationtype TEXT,
    address HSTORE,
    postcode TEXT,
    country_code VARCHAR(2)
  ){ts:search-data};
CREATE UNIQUE INDEX idx_osmline_place_id ON location_property_osmline USING BTREE (place_id) {ts:search-index};
CREATE INDEX idx_osmline_geometry_sector ON location_property_osmline USING BTREE (geometry_sector) {ts:address-index};
CREATE INDEX idx_osmline_linegeo ON location_property_osmline USING GIST (linegeo) {ts:search-index};
GRANT SELECT ON location_property_osmline TO "{www-user}";

drop table IF EXISTS search_name;
CREATE TABLE search_name (
  place_id BIGINT,
  importance FLOAT,
  search_rank SMALLINT,
  address_rank SMALLINT,
  name_vector integer[],
  nameaddress_vector integer[],
  country_code varchar(2)
  ) {ts:search-data};
SELECT AddGeometryColumn('search_name', 'centroid', 4326, 'GEOMETRY', 2);
CREATE INDEX idx_search_name_place_id ON search_name USING BTREE (place_id) {ts:search-index};

drop table IF EXISTS place_addressline;
CREATE TABLE place_addressline (
  place_id BIGINT,
  address_place_id BIGINT,
  distance FLOAT,
  cached_rank_address SMALLINT,
  fromarea boolean,
  isaddress boolean
  ) {ts:search-data};
CREATE INDEX idx_place_addressline_place_id on place_addressline USING BTREE (place_id) {ts:search-index};

drop table if exists placex;
CREATE TABLE placex (
  place_id BIGINT NOT NULL,
  parent_place_id BIGINT,
  linked_place_id BIGINT,
  importance FLOAT,
  indexed_date TIMESTAMP,
  geometry_sector INTEGER,
  rank_address SMALLINT,
  rank_search SMALLINT,
  partition SMALLINT,
  indexed_status SMALLINT,
  LIKE place INCLUDING CONSTRAINTS,
  wikipedia TEXT, -- calculated wikipedia article name (language:title)
  country_code varchar(2),
  housenumber TEXT,
  postcode TEXT
  ) {ts:search-data};
SELECT AddGeometryColumn('placex', 'centroid', 4326, 'GEOMETRY', 2);
CREATE UNIQUE INDEX idx_place_id ON placex USING BTREE (place_id) {ts:search-index};
CREATE INDEX idx_placex_osmid ON placex USING BTREE (osm_type, osm_id) {ts:search-index};
CREATE INDEX idx_placex_linked_place_id ON placex USING BTREE (linked_place_id) {ts:address-index} WHERE linked_place_id IS NOT NULL;
CREATE INDEX idx_placex_rank_search ON placex USING BTREE (rank_search, geometry_sector) {ts:address-index};
CREATE INDEX idx_placex_geometry ON placex USING GIST (geometry) {ts:search-index};
CREATE INDEX idx_placex_adminname on placex USING BTREE (make_standard_name(name->'name'),rank_search) {ts:address-index} WHERE osm_type='N' and rank_search < 26;

DROP SEQUENCE IF EXISTS seq_place;
CREATE SEQUENCE seq_place start 1;
GRANT SELECT on placex to "{www-user}" ;
GRANT SELECT ON search_name to "{www-user}" ;
GRANT SELECT on place_addressline to "{www-user}" ;
GRANT SELECT ON seq_word to "{www-user}" ;
GRANT SELECT ON planet_osm_ways to "{www-user}" ;
GRANT SELECT ON planet_osm_rels to "{www-user}" ;
GRANT SELECT on location_area to "{www-user}" ;

-- insert creates the location tables, creates location indexes if indexed == true
CREATE TRIGGER placex_before_insert BEFORE INSERT ON placex
    FOR EACH ROW EXECUTE PROCEDURE placex_insert();
CREATE TRIGGER osmline_before_insert BEFORE INSERT ON location_property_osmline
    FOR EACH ROW EXECUTE PROCEDURE osmline_insert();

-- update insert creates the location tables
CREATE TRIGGER placex_before_update BEFORE UPDATE ON placex
    FOR EACH ROW EXECUTE PROCEDURE placex_update();
CREATE TRIGGER osmline_before_update BEFORE UPDATE ON location_property_osmline
    FOR EACH ROW EXECUTE PROCEDURE osmline_update();

-- diff update triggers
CREATE TRIGGER placex_before_delete AFTER DELETE ON placex
    FOR EACH ROW EXECUTE PROCEDURE placex_delete();
CREATE TRIGGER place_before_delete BEFORE DELETE ON place
    FOR EACH ROW EXECUTE PROCEDURE place_delete();
CREATE TRIGGER place_before_insert BEFORE INSERT ON place
    FOR EACH ROW EXECUTE PROCEDURE place_insert();

-- Table for synthetic postcodes.
DROP TABLE IF EXISTS location_postcode;
CREATE TABLE location_postcode (
  place_id BIGINT,
  parent_place_id BIGINT,
  rank_search SMALLINT,
  rank_address SMALLINT,
  indexed_status SMALLINT,
  indexed_date TIMESTAMP,
  country_code varchar(2),
  postcode TEXT,
  geometry GEOMETRY(Geometry, 4326)
  );
CREATE INDEX idx_postcode_geometry ON location_postcode USING GIST (geometry) {ts:address-index};

CREATE TRIGGER location_postcode_before_update BEFORE UPDATE ON location_postcode
    FOR EACH ROW EXECUTE PROCEDURE postcode_update();

DROP TABLE IF EXISTS import_polygon_error;
CREATE TABLE import_polygon_error (
  osm_id BIGINT,
  osm_type CHAR(1),
  class TEXT NOT NULL,
  type TEXT NOT NULL,
  name HSTORE,
  country_code varchar(2),
  updated timestamp,
  errormessage text
  );
SELECT AddGeometryColumn('import_polygon_error', 'prevgeometry', 4326, 'GEOMETRY', 2);
SELECT AddGeometryColumn('import_polygon_error', 'newgeometry', 4326, 'GEOMETRY', 2);
CREATE INDEX idx_import_polygon_error_osmid ON import_polygon_error USING BTREE (osm_type, osm_id);
GRANT SELECT ON import_polygon_error TO "{www-user}";

DROP TABLE IF EXISTS import_polygon_delete;
CREATE TABLE import_polygon_delete (
  osm_id BIGINT,
  osm_type CHAR(1),
  class TEXT NOT NULL,
  type TEXT NOT NULL
  );
CREATE INDEX idx_import_polygon_delete_osmid ON import_polygon_delete USING BTREE (osm_type, osm_id);
GRANT SELECT ON import_polygon_delete TO "{www-user}";

DROP SEQUENCE IF EXISTS file;
CREATE SEQUENCE file start 1;

-- null table so it won't error
-- deliberately no drop - importing the table is expensive and static, if it is already there better to avoid removing it
CREATE TABLE wikipedia_article (
    language text NOT NULL,
    title text NOT NULL,
    langcount integer,
    othercount integer,
    totalcount integer,
    lat double precision,
    lon double precision,
    importance double precision,
    osm_type character(1),
    osm_id bigint
);
ALTER TABLE ONLY wikipedia_article ADD CONSTRAINT wikipedia_article_pkey PRIMARY KEY (language, title);
CREATE INDEX idx_wikipedia_article_osm_id ON wikipedia_article USING btree (osm_type, osm_id);

CREATE TABLE wikipedia_redirect (
    language text,
    from_title text,
    to_title text
);
ALTER TABLE ONLY wikipedia_redirect ADD CONSTRAINT wikipedia_redirect_pkey PRIMARY KEY (language, from_title);


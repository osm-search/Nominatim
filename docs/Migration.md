Database Migrations
===================

This page describes database migrations necessary to update existing databases
to newer versions of Nominatim.

SQL statements should be executed from the postgres commandline. Execute
`psql nominiatim` to enter command line mode.

3.0.0
-----

### Postcode Table

A new separate table for artificially computed postcode centroids was introduced.
Migration to the new format is possible but **not recommended**.

 * create postcode table and indexes, running the following SQL statements:

       CREATE TABLE location_postcode
         (place_id BIGINT, parent_place_id BIGINT, rank_search SMALLINT,
          rank_address SMALLINT, indexed_status SMALLINT, indexed_date TIMESTAMP,
          country_code varchar(2), postcode TEXT,
          geometry GEOMETRY(Geometry, 4326));
       CREATE INDEX idx_postcode_geometry ON location_postcode USING GIST (geometry);
       CREATE UNIQUE INDEX idx_postcode_id ON location_postcode USING BTREE (place_id);
       CREATE INDEX idx_postcode_postcode ON location_postcode USING BTREE (postcode);
       GRANT SELECT ON location_postcode TO "www-data";

 * add postcode column to location_area tables with SQL statement:

       ALTER TABLE location_area ADD COLUMN postcode TEXT;

 * reimport functions

       ./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions

 * create appropriate triggers with SQL:

       CREATE TRIGGER location_postcode_before_update BEFORE UPDATE ON location_postcode
         FOR EACH ROW EXECUTE PROCEDURE postcode_update();

 * populate postcode table (will take a while):

       ./utils/setup.php --calculate-postcodes --index --index-noanalyse

This will create a working database. You may also delete the old artificial
postcodes now. Note that this may be expensive and is not absolutely necessary.
The following SQL statement will remove them:

    DELETE FROM place_addressline a USING placex p
     WHERE a.address_place_id = p.place_id and p.osm_type = 'P';
    ALTER TABLE placex DISABLE TRIGGER USER;
    DELETE FROM placex WHERE osm_type = 'P';
    ALTER TABLE placex ENABLE TRIGGER USER;


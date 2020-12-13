# Database Migrations

This page describes database migrations necessary to update existing databases
to newer versions of Nominatim.

SQL statements should be executed from the PostgreSQL commandline. Execute
`psql nominatim` to enter command line mode.

## 3.5.0 -> 3.6.0

### Change of layout of search_name_* tables

The table need a different index for nearest place lookup. Recreate the
indexes using the following shell script:

```bash
for table in `psql -d nominatim -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'search_name_%'" -tA | grep -v search_name_blank`;
do
    psql -d nominatim -c "DROP INDEX idx_${table}_centroid_place; CREATE INDEX idx_${table}_centroid_place ON ${table} USING gist (centroid) WHERE ((address_rank >= 2) AND (address_rank <= 25)); DROP INDEX idx_${table}_centroid_street; CREATE INDEX idx_${table}_centroid_street ON ${table} USING gist (centroid) WHERE ((address_rank >= 26) AND (address_rank <= 27))";
done
```

### Removal of html output

The debugging UI is no longer directly provided with Nominatim. Instead we
now provide a simple Javascript application. Please refer to
[Setting up the Nominatim UI](../Setup-Nominatim-UI) for details on how to
set up the UI.

The icons served together with the API responses have been moved to the
nominatim-ui project as well. If you want to keep the `icon` field in the
response, you need to set `CONST_MapIcon_URL` to the URL of the `/mapicon`
directory of nominatim-ui.

### Change order during indexing

When reindexing places during updates, there is now a different order used
which needs a different database index. Create it with the following SQL command:

```sql
CREATE INDEX idx_placex_pendingsector_rank_address
  ON placex
  USING BTREE (rank_address, geometry_sector)
  WHERE indexed_status > 0;
```

You can then drop the old index with:

```sql
DROP INDEX idx_placex_pendingsector;
```

### Unused index

This index has been unused ever since the query using it was changed two years ago. Saves about 12GB on a planet installation.

```sql
DROP INDEX idx_placex_geometry_reverse_lookupPoint;
```

### Switching to dotenv

As part of the work changing the configuration format, the configuration for
the website is now using a separate configuration file. To create the
configuration file, run the following command after updating:

```sh
./utils/setup.php --setup-website
```

## 3.4.0 -> 3.5.0

### New Wikipedia/Wikidata importance tables

The `wikipedia_*` tables have a new format that also includes references to
Wikidata. You need to update the computation functions and the tables as
follows:

  * download the new Wikipedia tables as described in the import section
  * reimport the tables: `./utils/setup.php --import-wikipedia-articles`
  * update the functions: `./utils/setup.php --create-functions --enable-diff-updates`
  * create a new lookup index:
```sql
CREATE INDEX idx_placex_wikidata
  ON placex
  USING BTREE ((extratags -> 'wikidata'))
  WHERE extratags ? 'wikidata'
    AND class = 'place'
    AND osm_type = 'N'
    AND rank_search < 26;
```
  * compute importance: `./utils/update.php --recompute-importance`

The last step takes about 10 hours on the full planet.

Remove one function (it will be recreated in the next step):

```sql
DROP FUNCTION create_country(hstore,character varying);
```

Finally, update all SQL functions:

```sh
./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions
```

## 3.3.0 -> 3.4.0

### Reorganisation of location_area_country table

The table `location_area_country` has been optimized. You need to switch to the
new format when you run updates. While updates are disabled, run the following
SQL commands:

```sql
CREATE TABLE location_area_country_new AS
  SELECT place_id, country_code, geometry FROM location_area_country;
DROP TABLE location_area_country;
ALTER TABLE location_area_country_new RENAME TO location_area_country;
CREATE INDEX idx_location_area_country_geometry ON location_area_country USING GIST (geometry);
CREATE INDEX idx_location_area_country_place_id ON location_area_country USING BTREE (place_id);
```

Finally, update all SQL functions:

```sh
./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions
```

## 3.2.0 -> 3.3.0

### New database connection string (DSN) format

Previously database connection setting (`CONST_Database_DSN` in `settings/*.php`) had the format

   * (simple) `pgsql://@/nominatim`
   * (complex) `pgsql://johndoe:secret@machine1.domain.com:1234/db1`

The new format is

   * (simple) `pgsql:dbname=nominatim`
   * (complex) `pgsql:dbname=db1;host=machine1.domain.com;port=1234;user=johndoe;password=secret`

### Natural Earth country boundaries no longer needed as fallback

```sql
DROP TABLE country_naturalearthdata;
```

Finally, update all SQL functions:

```sh
./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions
```

### Configurable Address Levels

The new configurable address levels require a new table. Create it with the
following command:

```sh
./utils/update.php --update-address-levels
```

## 3.1.0 -> 3.2.0

### New reverse algorithm

The reverse algorithm has changed and requires new indexes. Run the following
SQL statements to create the indexes:

```sql
CREATE INDEX idx_placex_geometry_reverse_lookupPoint
  ON placex
  USING gist (geometry)
  WHERE (name IS NOT null or housenumber IS NOT null or rank_address BETWEEN 26 AND 27)
    AND class NOT IN ('railway','tunnel','bridge','man_made')
    AND rank_address >= 26
    AND indexed_status = 0
    AND linked_place_id IS null;
CREATE INDEX idx_placex_geometry_reverse_lookupPolygon
  ON placex USING gist (geometry)
  WHERE St_GeometryType(geometry) in ('ST_Polygon', 'ST_MultiPolygon')
    AND rank_address between 4 and 25
    AND type != 'postcode'
    AND name is not null
    AND indexed_status = 0
    AND linked_place_id is null;
CREATE INDEX idx_placex_geometry_reverse_placeNode
  ON placex USING gist (geometry)
  WHERE osm_type = 'N'
    AND rank_search between 5 and 25
    AND class = 'place'
    AND type != 'postcode'
    AND name is not null
    AND indexed_status = 0
    AND linked_place_id is null;
```

You also need to grant the website user access to the `country_osm_grid` table:

```sql
GRANT SELECT ON table country_osm_grid to "www-user";
```

Replace the `www-user` with the user name of your website server if necessary.

You can now drop the unused indexes:

```sql
DROP INDEX idx_placex_reverse_geometry;
```

Finally, update all SQL functions:

```sh
./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions
```

## 3.0.0 -> 3.1.0

### Postcode Table

A new separate table for artificially computed postcode centroids was introduced.
Migration to the new format is possible but **not recommended**.

Create postcode table and indexes, running the following SQL statements:

```sql
CREATE TABLE location_postcode
  (place_id BIGINT, parent_place_id BIGINT, rank_search SMALLINT,
   rank_address SMALLINT, indexed_status SMALLINT, indexed_date TIMESTAMP,
   country_code varchar(2), postcode TEXT,
   geometry GEOMETRY(Geometry, 4326));
CREATE INDEX idx_postcode_geometry ON location_postcode USING GIST (geometry);
CREATE UNIQUE INDEX idx_postcode_id ON location_postcode USING BTREE (place_id);
CREATE INDEX idx_postcode_postcode ON location_postcode USING BTREE (postcode);
GRANT SELECT ON location_postcode TO "www-data";
DROP TYPE IF EXISTS nearfeaturecentr CASCADE;
CREATE TYPE nearfeaturecentr AS (
  place_id BIGINT,
  keywords int[],
  rank_address smallint,
  rank_search smallint,
  distance float,
  isguess boolean,
  postcode TEXT,
  centroid GEOMETRY
);
```

Add postcode column to `location_area` tables with SQL statement:

```sql
ALTER TABLE location_area ADD COLUMN postcode TEXT;
```

Then reimport the functions:

```sh
./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions
```

Create appropriate triggers with SQL:

```sql
CREATE TRIGGER location_postcode_before_update BEFORE UPDATE ON location_postcode
    FOR EACH ROW EXECUTE PROCEDURE postcode_update();
```

Finally populate the postcode table (will take a while):

```sh
./utils/setup.php --calculate-postcodes --index --index-noanalyse
```

This will create a working database. You may also delete the old artificial
postcodes now. Note that this may be expensive and is not absolutely necessary.
The following SQL statement will remove them:

```sql
DELETE FROM place_addressline a USING placex p
 WHERE a.address_place_id = p.place_id and p.osm_type = 'P';
ALTER TABLE placex DISABLE TRIGGER USER;
DELETE FROM placex WHERE osm_type = 'P';
ALTER TABLE placex ENABLE TRIGGER USER;
```

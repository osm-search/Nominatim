# Database Migrations

This page describes database migrations necessary to update existing databases
to newer versions of Nominatim.

SQL statements should be executed from the postgres commandline. Execute
`psql nominatim` to enter command line mode.


## 3.2.0 -> master

### Natural Earth country boundaries no longer needed as fallback

```
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

```
CREATE INDEX idx_placex_geometry_reverse_lookupPoint
  ON placex USING gist (geometry)
  WHERE (name is not null or housenumber is not null or rank_address between 26 and 27)
    AND class not in ('railway','tunnel','bridge','man_made')
    AND rank_address >= 26 AND indexed_status = 0 AND linked_place_id is null;
CREATE INDEX idx_placex_geometry_reverse_lookupPolygon
  ON placex USING gist (geometry)
  WHERE St_GeometryType(geometry) in ('ST_Polygon', 'ST_MultiPolygon')
    AND rank_address between 4 and 25 AND type != 'postcode'
    AND name is not null AND indexed_status = 0 AND linked_place_id is null;
CREATE INDEX idx_placex_geometry_reverse_placeNode
  ON placex USING gist (geometry)
  WHERE osm_type = 'N' AND rank_search between 5 and 25
    AND class = 'place' AND type != 'postcode'
    AND name is not null AND indexed_status = 0 AND linked_place_id is null;
```

You also need to grant the website user access to the `country_osm_grid` table:

```
GRANT SELECT ON table country_osm_grid to "www-user";
```

Replace the `www-user` with the user name of your website server if necessary.

You can now drop the unused indexes:

```
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
drop type if exists nearfeaturecentr cascade;
create type nearfeaturecentr as (
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

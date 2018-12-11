# GB Postcodes


The server [importing instructions](https://www.nominatim.org/release-docs/latest/admin/Import-and-Update/) allow optionally download [`gb_postcode_data.sql.gz`](https://www.nominatim.org/data/gb_postcode_data.sql.gz). This document explains how the file got created.

## GB vs UK

GB (Great Britain) is more correct as the Ordnance Survey dataset doesn't contain postcodes from Northern Ireland.

## Importing separately after the initial import

If you forgot to download the file, or have a new version, you can import it separately:

1. Import the downloaded `gb_postcode_data.sql.gz` file.

2. Run the SQL query `SELECT count(getorcreate_postcode_id(postcode)) FROM gb_postcode;`. This will update the search index.

3. Run `utils/setup.php --calculate-postcodes` from the build directory. This will copy data form the `gb_postcode` table to the `location_postcodes` table.



## Converting Code-Point Open data

1. Download from [Code-Point® Open](https://www.ordnancesurvey.co.uk/business-and-government/products/code-point-open.html). It requires an email address where a download link will be send to.

2. `unzip codepo_gb.zip`

   Unpacked you'll see a directory of CSV files.

   ```
   $ more codepo_gb/Data/CSV/n.csv
   "N1 0AA",10,530626,183961,"E92000001","E19000003","E18000007","","E09000019","E05000368"
   "N1 0AB",10,530559,183978,"E92000001","E19000003","E18000007","","E09000019","E05000368"
   ```

   The coordinates are "Northings" and "Eastings" in [OSGB 1936](http://epsg.io/1314) projection. They can be projected to WGS84 like this

   ```
   SELECT ST_AsText(ST_Transform(ST_SetSRID('POINT(530626 183961)'::geometry,27700), 4326));
   POINT(-0.117872733220225 51.5394424719303)
   ```
   [-0.117872733220225 51.5394424719303 on OSM map](https://www.openstreetmap.org/?mlon=-0.117872733220225&mlat=51.5394424719303&zoom=16)



3. Create database, import CSV files, add geometry column, dump into file

   ```
   DBNAME=create_gb_postcode_file
   
   createdb $DBNAME
   echo 'CREATE EXTENSION postgis' | psql $DBNAME
   
   cat data/gb_postcode_table.sql | psql $DBNAME
   
   cat codepo_gb/Data/CSV/*.csv | ./data-sources/gb-postcodes/convert_codepoint.php | psql $DBNAME
   
   cat codepo_gb/Doc/licence.txt | iconv -f iso-8859-1 -t utf-8 | dos2unix | sed 's/^/-- /g' > gb_postcode_data.sql
   pg_dump -a -t gb_postcode $DBNAME | grep -v '^--' >> gb_postcode_data.sql
   
   gzip -9 -f gb_postcode_data.sql
   ls -lah gb_postcode_data.*
   
   # dropdb $DBNAME
   ```

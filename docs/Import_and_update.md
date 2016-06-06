Importing a new database
========================

The following instructions explain how to create a Nominatim database
from an OSM planet file and how to keep the database up to date. It
is assumed that you have already sucessfully installed the Nominatim
software itself, if not return to the [prerequisites page](Prerequisites.md).

Configuration setup in settings/local.php
-----------------------------------------

There are lots of configuration settings you can tweak. Have a look
at `settings/settings.php` for a full list. Most should have a sensible default.
If you plan to import a large dataset (e.g. Europe, North America, planet),
you should also enable flatnode storage of node locations. With this
setting enabled, node coordinates are stored in a simple file instead
of the database. This will save you import time and disk storage.
Add to your settings/local.php:

    @define('CONST_Osm2pgsql_Flatnode_File', '/path/to/flatnode.file');


Downloading additional data
---------------------------

### Wikipedia rankings

Wikipedia can be used as an optional auxiliary data source to help indicate
the importance of osm features. Nominatim will work without this information
but it will improve the quality of the results if this is installed.
This data is available as a binary download:

    cd $NOMINATIM_SOURCE_DIR/data
    wget http://www.nominatim.org/data/wikipedia_article.sql.bin
    wget http://www.nominatim.org/data/wikipedia_redirect.sql.bin

Combined the 2 files are around 1.5GB and add around 30GB to the install
size of nominatim. They also increase the install time by an hour or so.

### UK postcodes

Nominatim can use postcodes from an external source to improve searches that involve a UK postcode. This data can be optionally downloaded: 

    cd $NOMINATIM_SOURCE_DIR/data
    wget http://www.nominatim.org/data/gb_postcode_data.sql.gz


Initial Import of the Data
--------------------------

**Important:** first try the import with a small excerpt, for example from Geofabrik.

Download the data to import and load the data with the following command:

    ./utils/setup.php --osm-file <your data file> --all [--osm2pgsql-cache 28000] 2>&1 | tee setup.log

The --osm2pgsql-cache parameter is optional but strongly recommended for
planet imports. It sets the node cache size for the osm2pgsql import part
(see -C parameter in osm2pgsql help). 28GB are recommended for a full planet
imports, for excerpts you can use less.
Adapt to your available RAM to avoid swapping.

The import will take as little as an hour for a small country extract
and as much as 10 days for a full-scale planet import on less powerful
hardware.


Loading Additional Datasets
---------------------------

The following commands will create additional entries for countries and POI searches:

    ./utils/specialphrases.php --countries > data/specialphrases_countries.sql
    psql -d nominatim -f data/specialphrases_countries.sql
    ./utils/specialphrases.php --wiki-import > data/specialphrases.sql
    psql -d nominatim -f data/specialphrases.sql


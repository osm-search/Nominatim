Importing a new database
========================

The following instructions explain how to create a Nominatim database
from an OSM planet file and how to keep the database up to date. It
is assumed that you have already successfully installed the Nominatim
software itself, if not return to the [installation page](Installation.md).

Configuration setup in settings/local.php
-----------------------------------------

There are lots of configuration settings you can tweak. Have a look
at `settings/settings.php` for a full list. Most should have a sensible default.
If you plan to import a large dataset (e.g. Europe, North America, planet),
you should also enable flatnode storage of node locations. With this
setting enabled, node coordinates are stored in a simple file instead
of the database. This will save you import time and disk storage.
Add to your `settings/local.php`:

    @define('CONST_Osm2pgsql_Flatnode_File', '/path/to/flatnode.file');

Replace the second part with a suitable path on your system and make sure
the directory exists. There should be at least 35GB of free space.

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


Initial import of the data
--------------------------

**Important:** first try the import with a small excerpt, for example from
[Geofabrik](http://download.geofabrik.de).

Download the data to import and load the data with the following command:

    ./utils/setup.php --osm-file <your data file> --all [--osm2pgsql-cache 28000] 2>&1 | tee setup.log

The `--osm2pgsql-cache` parameter is optional but strongly recommended for
planet imports. It sets the node cache size for the osm2pgsql import part
(see `-C` parameter in osm2pgsql help). 28GB are recommended for a full planet
import, for excerpts you can use less. Adapt to your available RAM to
avoid swapping, never give more than 2/3 of RAM to osm2pgsql.


Loading additional datasets
---------------------------

The following commands will create additional entries for POI searches:

    ./utils/specialphrases.php --wiki-import > specialphrases.sql
    psql -d nominatim -f specialphrases.sql


Installing Tiger housenumber data for the US
============================================

Nominatim is able to use the official TIGER address set to complement the
OSM housenumber data in the US. You can add TIGER data to your own Nominatim
instance by following these steps:

  1. Install the GDAL library and python bindings and the unzip tool

       * Ubuntu: `sudo apt-get install python-gdal unzip`
       * CentOS: `sudo yum install gdal-python unzip`

  2. Get the TIGER 2016 data. You will need the EDGES files
     (3,234 zip files, 11GB total)

         wget -r ftp://ftp2.census.gov/geo/tiger/TIGER2016/EDGES/

     The first one is the original source, the second a considerably faster
     mirror.

  3. Convert the data into SQL statements (stored in data/tiger): 

         ./utils/imports.php --parse-tiger <tiger edge data directory>

  4. Import the data into your Nominatim database: 

         ./utils/setup.php --import-tiger-data

  5. Enable use of the Tiger data in your `settings/local.php` by adding:

         @define('CONST_Use_US_Tiger_Data', true);

  6. Apply the new settings:

        ./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions

Be warned that the import can take a very long time, especially if you
import all of the US. The entire US adds about 10GB to your database.


Updates
=======

There are many different possibilities to update your Nominatim database.
The following section describes how to keep it up-to-date with Pyosmium.
For a list of other methods see the output of `./utils/update.php --help`.

Installing the newest version of Pyosmium
-----------------------------------------

It is recommended to install Pyosmium via pip:

    pip install --user osmium

Nominatim needs a tool called `pyosmium-get-updates` that comes with
Pyosmium. You need to tell Nominatim where to find it. Add the
following line to your `settings/local.php`:

    @define('CONST_Pyosmium_Binary', '/home/user/.local/bin/pyosmium-get-changes');

The path above is fine if you used the `--user` parameter with pip.
Replace `user` with your user name.

Setting up the update process
-----------------------------

Next the update needs to be initialised. By default Nominatim is configured
to update using the global minutely diffs.

If you want a different update source you will need to add some settings
to `settings/local.php`. For example, to use the daily country extracts
diffs for Ireland from geofabrik add the following:

    // base URL of the replication service
    @define('CONST_Replication_Url', 'http://download.geofabrik.de/europe/ireland-and-northern-ireland-updates');
    // How often upstream publishes diffs
    @define('CONST_Replication_Update_Interval', '86400');
    // How long to sleep if no update found yet
    @define('CONST_Replication_Recheck_Interval', '900');

To set up the update process now run the following command:

    ./utils/update --init-updates

It outputs the date where updates will start. Recheck that this date is
what you expect.

The --init-updates command needs to be rerun whenever the replication service
is changed.

Updating Nominatim
------------------

The following command will keep your database constantly up to date:

    ./utils/update.php --import-osmosis-all

If you have imported multiple country extracts and want to keep them
up-to-date, have a look at the script in
[issue #60](https://github.com/openstreetmap/Nominatim/issues/60).


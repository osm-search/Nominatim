# Importing and Updating the Database

The following instructions explain how to create a Nominatim database
from an OSM planet file and how to keep the database up to date. It
is assumed that you have already successfully installed the Nominatim
software itself, if not return to the [installation page](Installation.md).

## Configuration setup in settings/local.php

The Nominatim server can be customized via the file `settings/local.php`
in the build directory. Note that this is a PHP file, so it must always
start like this:

    <?php

without any leading spaces.

There are lots of configuration settings you can tweak. Have a look
at `settings/default.php` for a full list. Most should have a sensible default.

#### Flatnode files

If you plan to import a large dataset (e.g. Europe, North America, planet),
you should also enable flatnode storage of node locations. With this
setting enabled, node coordinates are stored in a simple file instead
of the database. This will save you import time and disk storage.
Add to your `settings/local.php`:

    @define('CONST_Osm2pgsql_Flatnode_File', '/path/to/flatnode.file');

Replace the second part with a suitable path on your system and make sure
the directory exists. There should be at least 40GB of free space.

## Downloading additional data

### Wikipedia rankings

Wikipedia can be used as an optional auxiliary data source to help indicate
the importance of osm features. Nominatim will work without this information
but it will improve the quality of the results if this is installed.
This data is available as a binary download:

    cd $NOMINATIM_SOURCE_DIR/data
    wget https://www.nominatim.org/data/wikipedia_article.sql.bin
    wget https://www.nominatim.org/data/wikipedia_redirect.sql.bin

Combined the 2 files are around 1.5GB and add around 30GB to the install
size of nominatim. They also increase the install time by an hour or so.

*NOTE:* you'll need to download the Wikipedia rankings before performing
the initial import of the data if you want the rankings applied to the
loaded data.

### UK postcodes

Nominatim can use postcodes from an external source to improve searches that involve a UK postcode. This data can be optionally downloaded: 

    cd $NOMINATIM_SOURCE_DIR/data
    wget https://www.nominatim.org/data/gb_postcode_data.sql.gz

## Choosing the Data to Import

In its default setup Nominatim is configured to import the full OSM data
set for the entire planet. Such a setup requires a powerful machine with
at least 32GB of RAM and around 800GB of SSD hard disks. Depending on your
use case there are various ways to reduce the amount of data imported. This
section discusses these methods. They can also be combined.

### Using an extract

If you only need geocoding for a smaller region, then precomputed extracts
are a good way to reduce the database size and import time.
[Geofabrik](https://download.geofabrik.de) offers extracts for most countries.
They even have daily updates which can be used with the update process described
below. There are also
[other providers for extracts](https://wiki.openstreetmap.org/wiki/Planet.osm#Downloading).

Please be aware that some extracts are not cut exactly along the country
boundaries. As a result some parts of the boundary may be missing which means
that cannot compute the areas for some administrative areas.

### Dropping Data Required for Dynamic Updates

About half of the data in Nominatim's database is not really used for serving
the API. It is only there to allow the data to be updated from the latest
changes from OSM. For many uses these dynamic updates are not really required.
If you don't plan to apply updates, the dynamic part of the database can be
safely dropped using the following command:

```
./utils/setup.php --drop
```

Note that you still need to provide for sufficient disk space for the initial
import. So this option is particularly interesting if you plan to transfer the
database or reuse the space later.

### Reverse-only Imports

If you only want to use the Nominatim database for reverse lookups or
if you plan to use the installation only for exports to a
[photon](http://photon.komoot.de/) database, then you can set up a database
without search indexes. Add `--reverse-only` to your setup command above.

This saves about 5% of disk space.

### Filtering Imported Data

Nominatim normally sets up a full search database containing administrative
boundaries, places, streets, addresses and POI data. There are also other
import styles available which only read selected data:

* **settings/import-admin.style**
  Only import administrative boundaries and places.
* **settings/import-street.style**
  Like the admin style but also adds streets.
* **settings/import-address.style**
  Import all data necessary to compute addresses down to house number level.
* **settings/import-full.style**
  Default style that also includes points of interest.

The style can be changed with the configuration `CONST_Import_Style`.

To give you an idea of the impact of using the different style, the table
below gives rough estimates of the final database size after import of a
2018 planet and after using the `--drop` option. It also shows the time
needed for the import on a machine with 32GB RAM, 4 CPUS and SSDs. Note that
the given sizes are just an estimate meant for comparison of style requirements.
Your planet import is likely to be larger as the OSM data grows with time.

style     | Import time  |  DB size   |  after drop
----------|--------------|------------|------------
admin     |    5h        |  190 GB    |   20 GB
street    |   42h        |  400 GB    |  180 GB
address   |   59h        |  500 GB    |  260 GB
full      |   80h        |  590 GB    |  320 GB

You can also customize the styles further. For an description of the
style format see [the developement section](../develop/Import.md).

## Initial import of the data

**Important:** first try the import with a small extract, for example from
[Geofabrik](https://download.geofabrik.de).

Download the data to import and load the data with the following command:

```sh
./utils/setup.php --osm-file <data file> --all [--osm2pgsql-cache 28000] 2>&1 | tee setup.log
```

The `--osm2pgsql-cache` parameter is optional but strongly recommended for
planet imports. It sets the node cache size for the osm2pgsql import part
(see `-C` parameter in osm2pgsql help). As a rule of thumb, this should be
about the same size as the file you are importing but never more than
2/3 of RAM available. If your machine starts swapping reduce the size.

Computing word frequency for search terms can improve the performance of
forward geocoding in particular under high load as it helps Postgres' query
planner to make the right decisions. To recompute word counts run:

```sh
./utils/update.php --recompute-word-counts
```

This will take a couple of hours for a full planet installation. You can
also defer that step to a later point in time when you realise that
performance becomes an issue. Just make sure that updates are stopped before
running this function.

If you want to be able to search for places by their type through
[special key phrases](https://wiki.openstreetmap.org/wiki/Nominatim/Special_Phrases)
you also need to enable these key phrases like this:

    ./utils/specialphrases.php --wiki-import > specialphrases.sql
    psql -d nominatim -f specialphrases.sql

Note that this command downloads the phrases from the wiki link above.


## Installing Tiger housenumber data for the US

Nominatim is able to use the official [TIGER](https://www.census.gov/geo/maps-data/data/tiger.html)
address set to complement the OSM house number data in the US. You can add
TIGER data to your own Nominatim instance by following these steps. The
entire US adds about 10GB to your database.

  1. Get preprocessed TIGER 2018 data and unpack it into the
     data directory in your Nominatim sources:

        cd Nominatim/data
        wget https://nominatim.org/data/tiger2018-nominatim-preprocessed.tar.gz
        tar xf tiger2018-nominatim-preprocessed.tar.gz

    `data-source/us-tiger/README.md` explains how the data got preprocessed.

  2. Import the data into your Nominatim database: 

        ./utils/setup.php --import-tiger-data

  3. Enable use of the Tiger data in your `settings/local.php` by adding:

         @define('CONST_Use_US_Tiger_Data', true);

  4. Apply the new settings:

```sh
    ./utils/setup.php --create-functions --enable-diff-updates --create-partition-functions
```


## Updates

There are many different possibilities to update your Nominatim database.
The following section describes how to keep it up-to-date with Pyosmium.
For a list of other methods see the output of `./utils/update.php --help`.

#### Installing the newest version of Pyosmium

It is recommended to install Pyosmium via pip. Run (as the same user who
will later run the updates):

```sh
pip install --user osmium
```

Nominatim needs a tool called `pyosmium-get-updates`, which comes with
Pyosmium. You need to tell Nominatim where to find it. Add the
following line to your `settings/local.php`:

    @define('CONST_Pyosmium_Binary', '/home/user/.local/bin/pyosmium-get-changes');

The path above is fine if you used the `--user` parameter with pip.
Replace `user` with your user name.

#### Setting up the update process

Next the update needs to be initialised. By default Nominatim is configured
to update using the global minutely diffs.

If you want a different update source you will need to add some settings
to `settings/local.php`. For example, to use the daily country extracts
diffs for Ireland from geofabrik add the following:

    // base URL of the replication service
    @define('CONST_Replication_Url', 'https://download.geofabrik.de/europe/ireland-and-northern-ireland-updates');
    // How often upstream publishes diffs
    @define('CONST_Replication_Update_Interval', '86400');
    // How long to sleep if no update found yet
    @define('CONST_Replication_Recheck_Interval', '900');

To set up the update process now run the following command:

    ./utils/update.php --init-updates

It outputs the date where updates will start. Recheck that this date is
what you expect.

The --init-updates command needs to be rerun whenever the replication service
is changed.

#### Updating Nominatim

The following command will keep your database constantly up to date:

    ./utils/update.php --import-osmosis-all

(Note that even though the old name "import-osmosis-all" has been kept for compatibility reasons, Osmosis is not required to run this - it uses pyosmium behind the scenes.)

If you have imported multiple country extracts and want to keep them
up-to-date, have a look at the script in
[issue #60](https://github.com/openstreetmap/Nominatim/issues/60).


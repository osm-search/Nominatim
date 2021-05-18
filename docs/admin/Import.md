# Importing the Database

The following instructions explain how to create a Nominatim database
from an OSM planet file. It is assumed that you have already successfully
installed the Nominatim software itself and the `nominatim` tool can be found
in your `PATH`. If this is not the case, return to the
[installation page](Installation.md).

## Creating the project directory

Before you start the import, you should create a project directory for your
new database installation. This directory receives all data that is related
to a single Nominatim setup: configuration, extra data, etc. Create a project
directory apart from the Nominatim software and change into the directory:

```
mkdir ~/nominatim-planet
cd ~/nominatim-planet
```

In the following, we refer to the project directory as `$PROJECT_DIR`. To be
able to copy&paste instructions, you can export the appropriate variable:

```
export PROJECT_DIR=~/nominatim-planet
```

The Nominatim tool assumes per default that the current working directory is
the project directory but you may explicitly state a different directory using
the `--project-dir` parameter. The following instructions assume that you run
all commands from the project directory.

!!! tip "Migration Tip"

    Nominatim used to be run directly from the build directory until version 3.6.
    Essentially, the build directory functioned as the project directory
    for the database installation. This setup still works and can be useful for
    development purposes. It is not recommended anymore for production setups.
    Create a project directory that is separate from the Nominatim software.

### Configuration setup in `.env`

The Nominatim server can be customized via an `.env` configuration file in the
project directory. This is a file in [dotenv](https://github.com/theskumar/python-dotenv)
format which looks the same as variable settings in a standard shell environment.
You can also set the same configuration via environment variables. All
settings have a `NOMINATIM_` prefix to avoid conflicts with other environment
variables.

There are lots of configuration settings you can tweak. Have a look
at `settings/env.default` for a full list. Most should have a sensible default.

#### Flatnode files

If you plan to import a large dataset (e.g. Europe, North America, planet),
you should also enable flatnode storage of node locations. With this
setting enabled, node coordinates are stored in a simple file instead
of the database. This will save you import time and disk storage.
Add to your `.env`:

    NOMINATIM_FLATNODE_FILE="/path/to/flatnode.file"

Replace the second part with a suitable path on your system and make sure
the directory exists. There should be at least 75GB of free space.

## Downloading additional data

### Wikipedia/Wikidata rankings

Wikipedia can be used as an optional auxiliary data source to help indicate
the importance of OSM features. Nominatim will work without this information
but it will improve the quality of the results if this is installed.
This data is available as a binary download. Put it into your project directory:

    cd $PROJECT_DIR
    wget https://www.nominatim.org/data/wikimedia-importance.sql.gz

The file is about 400MB and adds around 4GB to the Nominatim database.

!!! tip
    If you forgot to download the wikipedia rankings, you can also add
    importances after the import. Download the files, then run
    `nominatim refresh --wiki-data --importance`. Updating importances for
    a planet can take a couple of hours.

### External postcodes

Nominatim can use postcodes from an external source to improve searching with
postcodes. We provide precomputed postcodes sets for the US (using TIGER data)
and the UK (using the [CodePoint OpenData set](https://osdatahub.os.uk/downloads/open/CodePointOpen).
This data can be optionally downloaded into the project directory:

    cd $PROJECT_DIR
    wget https://www.nominatim.org/data/gb_postcodes.csv.gz
    wget https://www.nominatim.org/data/us_postcodes.csv.gz

You can also add your own custom postcode sources, see
[Customization of postcodes](Customization.md#external-postcode-data).

## Choosing the data to import

In its default setup Nominatim is configured to import the full OSM data
set for the entire planet. Such a setup requires a powerful machine with
at least 64GB of RAM and around 900GB of SSD hard disks. Depending on your
use case there are various ways to reduce the amount of data imported. This
section discusses these methods. They can also be combined.

### Using an extract

If you only need geocoding for a smaller region, then precomputed OSM extracts
are a good way to reduce the database size and import time.
[Geofabrik](https://download.geofabrik.de) offers extracts for most countries.
They even have daily updates which can be used with the update process described
[in the next section](../Update). There are also
[other providers for extracts](https://wiki.openstreetmap.org/wiki/Planet.osm#Downloading).

Please be aware that some extracts are not cut exactly along the country
boundaries. As a result some parts of the boundary may be missing which means
that Nominatim cannot compute the areas for some administrative areas.

### Dropping Data Required for Dynamic Updates

About half of the data in Nominatim's database is not really used for serving
the API. It is only there to allow the data to be updated from the latest
changes from OSM. For many uses these dynamic updates are not really required.
If you don't plan to apply updates, you can run the import with the
`--no-updates` parameter. This will drop the dynamic part of the database as
soon as it is not required anymore.

You can also drop the dynamic part later using the following command:

```
nominatim freeze
```

Note that you still need to provide for sufficient disk space for the initial
import. So this option is particularly interesting if you plan to transfer the
database or reuse the space later.

### Reverse-only Imports

If you only want to use the Nominatim database for reverse lookups or
if you plan to use the installation only for exports to a
[photon](https://photon.komoot.de/) database, then you can set up a database
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
* **settings/import-extratags.style**
  Like the full style but also adds most of the OSM tags into the extratags
  column.

The style can be changed with the configuration `NOMINATIM_IMPORT_STYLE`.

To give you an idea of the impact of using the different styles, the table
below gives rough estimates of the final database size after import of a
2020 planet and after using the `--drop` option. It also shows the time
needed for the import on a machine with 64GB RAM, 4 CPUS and NVME disks.
Note that the given sizes are just an estimate meant for comparison of
style requirements. Your planet import is likely to be larger as the
OSM data grows with time.

style     | Import time  |  DB size   |  after drop
----------|--------------|------------|------------
admin     |    4h        |  215 GB    |   20 GB
street    |   22h        |  440 GB    |  185 GB
address   |   36h        |  545 GB    |  260 GB
full      |   54h        |  640 GB    |  330 GB
extratags |   54h        |  650 GB    |  340 GB

You can also customize the styles further.
A [description of the style format](../develop/Import.md#configuring-the-import) 
can be found in the development section.

## Initial import of the data

!!! danger "Important"
    First try the import with a small extract, for example from
    [Geofabrik](https://download.geofabrik.de).

Download the data to import. Then issue the following command
from the **build directory** to start the import:

```sh
nominatim import --osm-file <data file> 2>&1 | tee setup.log
```

### Notes on full planet imports

Even on a perfectly configured machine
the import of a full planet takes around 2 days. Once you see messages
with `Rank .. ETA` appear, the indexing process has started. This part takes
the most time. There are 30 ranks to process. Rank 26 and 30 are the most complex.
They take each about a third of the total import time. If you have not reached
rank 26 after two days of import, it is worth revisiting your system
configuration as it may not be optimal for the import.

### Notes on memory usage

In the first step of the import Nominatim uses [osm2pgsql](https://osm2pgsql.org)
to load the OSM data into the PostgreSQL database. This step is very demanding
in terms of RAM usage. osm2pgsql and PostgreSQL are running in parallel at 
this point. PostgreSQL blocks at least the part of RAM that has been configured
with the `shared_buffers` parameter during
[PostgreSQL tuning](Installation#postgresql-tuning)
and needs some memory on top of that. osm2pgsql needs at least 2GB of RAM for
its internal data structures, potentially more when it has to process very large
relations. In addition it needs to maintain a cache for node locations. The size
of this cache can be configured with the parameter `--osm2pgsql-cache`.

When importing with a flatnode file, it is best to disable the node cache
completely and leave the memory for the flatnode file. Nominatim will do this
by default, so you do not need to configure anything in this case.

For imports without a flatnode file, set `--osm2pgsql-cache` approximately to
the size of the OSM pbf file you are importing. The size needs to be given in
MB. Make sure you leave enough RAM for PostgreSQL and osm2pgsql as mentioned
above. If the system starts swapping or you are getting out-of-memory errors,
reduce the cache size or even consider using a flatnode file.


### Testing the installation

Run this script to verify all required tables and indices got created successfully.

```sh
nominatim admin --check-database
```

Now you can try out your installation by running:

```sh
nominatim serve
```

This runs a small test server normally used for development. You can use it
to verify that your installation is working. Go to
`http://localhost:8088/status.php` and you should see the message `OK`.
You can also run a search query, e.g. `http://localhost:8088/search.php?q=Berlin`.

Note that search query is not supported for reverse-only imports. You can run a
reverse query, e.g. `http://localhost:8088/reverse.php?lat=27.1750090510034&lon=78.04209025`.

To run Nominatim via webservers like Apache or nginx, please read the
[Deployment chapter](Deployment.md).

## Tuning the database

Accurate word frequency information for search terms helps PostgreSQL's query
planner to make the right decisions. Recomputing them can improve the performance
of forward geocoding in particular under high load. To recompute word counts run:

```sh
nominatim refresh --word-counts
```

This will take a couple of hours for a full planet installation. You can
also defer that step to a later point in time when you realise that
performance becomes an issue. Just make sure that updates are stopped before
running this function.

If you want to be able to search for places by their type through
[special key phrases](https://wiki.openstreetmap.org/wiki/Nominatim/Special_Phrases)
you also need to import these key phrases like this:

```sh
nominatim special-phrases --import-from-wiki
```

Note that this command downloads the phrases from the wiki link above. You
need internet access for the step.

You can also import special phrases from a csv file, for more 
information please read the [Customization chapter](Customization.md).

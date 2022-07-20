# Advanced installations

This page contains instructions for setting up multiple countries in 
your Nominatim database. It is assumed that you have already successfully
installed the Nominatim software itself, if not return to the 
[installation page](Installation.md).

## Importing multiple regions (without updates)

To import multiple regions in your database you can simply give multiple
OSM files to the import command:

```
nominatim import --osm-file file1.pbf --osm-file file2.pbf
```

If you already have imported a file and want to add another one, you can
use the add-data function to import the additional data as follows:

```
nominatim add-data --file <FILE>
nominatim refresh --postcodes
nominatim index -j <NUMBER OF THREADS>
```

Please note that adding additional data is always significantly slower than
the original import.

## Importing multiple regions (with updates)

If you want to import multiple regions _and_ be able to keep them up-to-date
with updates, then you can use the scripts provided in the `utils` directory.

These scripts will set up an `update` directory in your project directory,
which has the following structure:

```bash
update
    ├── europe
    │   ├── andorra
    │   │   └── sequence.state
    │   └── monaco
    │       └── sequence.state
    └── tmp
        └── europe
                ├── andorra-latest.osm.pbf
                └── monaco-latest.osm.pbf


```

The `sequence.state` files contain the sequence ID for each region. They will
be used by pyosmium to get updates. The `tmp` folder is used for import dump and
can be deleted once the import is complete.


### Setting up multiple regions

Create a project directory as described for the
[simple import](Import.md#creating-the-project-directory). If necessary,
you can also add an `.env` configuration with customized options. In particular,
you need to make sure that `NOMINATIM_REPLICATION_UPDATE_INTERVAL` and
`NOMINATIM_REPLICATION_RECHECK_INTERVAL` are set according to the update
interval of the extract server you use.

Copy the scripts `utils/import_multiple_regions.sh` and `utils/update_database.sh`
into the project directory.

Now customize both files as per your requirements

1. List of countries. e.g.

        COUNTRIES="europe/monaco europe/andorra"

2. URL to the service providing the extracts and updates. eg:

        BASEURL="https://download.geofabrik.de"
        DOWNCOUNTRYPOSTFIX="-latest.osm.pbf"

5. Followup in the update script can be set according to your installation.
   E.g. for Photon,

        FOLLOWUP="curl http://localhost:2322/nominatim-update"

    will handle the indexing.


To start the initial import, change into the project directory and run

```
    bash import_multiple_regions.sh
```

### Updating the database

Change into the project directory and run the following command:

    bash update_database.sh

This will get diffs from the replication server, import diffs and index
the database. The default replication server in the
script([Geofabrik](https://download.geofabrik.de)) provides daily updates.

## Using an external PostgreSQL database

You can install Nominatim using a database that runs on a different server when
you have physical access to the file system on the other server. Nominatim
uses a custom normalization library that needs to be made accessible to the
PostgreSQL server. This section explains how to set up the normalization
library.

!!! note
    The external module is only needed when using the legacy tokenizer.
    If you have chosen the ICU tokenizer, then you can ignore this section
    and follow the standard import documentation.

### Option 1: Compiling the library on the database server

The most sure way to get a working library is to compile it on the database
server. From the prerequisites you need at least cmake, gcc and the
PostgreSQL server package.

Clone or unpack the Nominatim source code, enter the source directory and
create and enter a build directory.

```sh
cd Nominatim
mkdir build
cd build
```

Now configure cmake to only build the PostgreSQL module and build it:

```
cmake -DBUILD_IMPORTER=off -DBUILD_API=off -DBUILD_TESTS=off -DBUILD_DOCS=off -DBUILD_OSM2PGSQL=off ..
make
```

When done, you find the normalization library in `build/module/nominatim.so`.
Copy it to a place where it is readable and executable by the PostgreSQL server
process.

### Option 2: Compiling the library on the import machine

You can also compile the normalization library on the machine from where you
run the import.

!!! important
    You can only do this when the database server and the import machine have
    the same architecture and run the same version of Linux. Otherwise there is
    no guarantee that the compiled library is compatible with the PostgreSQL
    server running on the database server.

Make sure that the PostgreSQL server package is installed on the machine
**with the same version as on the database server**. You do not need to install
the PostgreSQL server itself.

Download and compile Nominatim as per standard instructions. Once done, you find
the normalization library in `build/module/nominatim.so`. Copy the file to
the database server at a location where it is readable and executable by the
PostgreSQL server process.

### Running the import

On the client side you now need to configure the import to point to the
correct location of the library **on the database server**. Add the following
line to your your `.env` file:

```php
NOMINATIM_DATABASE_MODULE_PATH="<directory on the database server where nominatim.so resides>"
```

Now change the `NOMINATIM_DATABASE_DSN` to point to your remote server and continue
to follow the [standard instructions for importing](Import.md).


## Moving the database to another machine

For some configurations it may be useful to run the import on one machine, then
move the database to another machine and run the Nominatim service from there.
For example, you might want to use a large machine to be able to run the import
quickly but only want a smaller machine for production because there is not so
much load. Or you might want to do the import once and then replicate the
database to many machines.

The important thing to keep in mind when transferring the Nominatim installation
is that you need to transfer the database _and the project directory_. Both
parts are essential for your installation.

The Nominatim database can be transferred using the `pg_dump`/`pg_restore` tool.
Make sure to use the same version of PostgreSQL and PostGIS on source and
target machine.

!!! note
    Before creating a dump of your Nominatim database, consider running
    `nominatim freeze` first. Your database looses the ability to receive further
    data updates but the resulting database is only about a third of the size
    of a full database.

Next install Nominatim on the target machine by following the standard installation
instructions. Again, make sure to use the same version as the source machine.

Create a project directory on your destination machine and set up the `.env`
file to match the configuration on the source machine. Finally run

    nominatim refresh --website

to make sure that the local installation of Nominatim will be used.

If you are using the legacy tokenizer you might also have to switch to the
PostgreSQL module that was compiled on your target machine. If you get errors
that PostgreSQL cannot find or access `nominatim.so` then rerun

   nominatim refresh --functions

on the target machine to update the the location of the module.

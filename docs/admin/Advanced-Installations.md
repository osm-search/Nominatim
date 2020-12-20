# Advanced installations

This page contains instructions for setting up multiple countries in 
your Nominatim database. It is assumed that you have already successfully
installed the Nominatim software itself, if not return to the 
[installation page](Installation.md).

## Importing multiple regions

To import multiple regions in your database, you need to configure and run `utils/import_multiple_regions.sh` file. This script will set up the update directory which has the following structure:

```bash
update
    ├── europe
    │   ├── andorra
    │   │   └── sequence.state
    │   └── monaco
    │       └── sequence.state
    └── tmp
        ├── combined.osm.pbf
        └── europe
                ├── andorra-latest.osm.pbf
                └── monaco-latest.osm.pbf


```

The `sequence.state` files will contain the sequence ID, which will be used by pyosmium to get updates. The tmp folder is used for import dump.

### Configuring multiple regions

The file `import_multiple_regions.sh` needs to be edited as per your requirement:

1. List of countries. eg:

        COUNTRIES="europe/monaco europe/andorra"

2. Path to Build directory. eg:

        NOMINATIMBUILD="/srv/nominatim/build"

3. Path to Update directory. eg:
        
        UPDATEDIR="/srv/nominatim/update"

4. Replication URL. eg:
    
        BASEURL="https://download.geofabrik.de"
        DOWNCOUNTRYPOSTFIX="-latest.osm.pbf"
 
!!! tip
    If your database already exists and you want to add more countries, replace the setting up part
    `${SETUPFILE} --osm-file ${UPDATEDIR}/tmp/combined.osm.pbf --all 2>&1`
    with `${UPDATEFILE} --import-file ${UPDATEDIR}/tmp/combined.osm.pbf --index --index-instances N 2>&1`
    where N is the numbers of CPUs in your system.

### Setting up multiple regions

Run the following command from your Nominatim directory after configuring the file.

    bash ./utils/import_multiple_regions.sh

!!! danger "Important"
        This file uses osmium-tool. It must be installed before executing the import script.
        Installation instructions can be found [here](https://osmcode.org/osmium-tool/manual.html#installation).

### Updating multiple regions

To import multiple regions in your database, you need to configure and run ```utils/update_database.sh```.
This uses the update directory set up while setting up the DB.   

### Configuring multiple regions

The file `update_database.sh` needs to be edited as per your requirement:

1. List of countries. eg:

        COUNTRIES="europe/monaco europe/andorra"

2. Path to Build directory. eg:

        NOMINATIMBUILD="/srv/nominatim/build"

3. Path to Update directory. eg:
        
        UPDATEDIR="/srv/nominatim/update"

4. Replication URL. eg:
    
        BASEURL="https://download.geofabrik.de"
        DOWNCOUNTRYPOSTFIX="-updates"

5. Followup can be set according to your installation. eg: For Photon,

        FOLLOWUP="curl http://localhost:2322/nominatim-update"

    will handle the indexing.

### Updating the database

Run the following command from your Nominatim directory after configuring the file.

    bash ./utils/update_database.sh

This will get diffs from the replication server, import diffs and index the database. The default replication server in the script([Geofabrik](https://download.geofabrik.de)) provides daily updates.

## Importing Nominatim to an external PostgreSQL database

You can install Nominatim using a database that runs on a different server when
you have physical access to the file system on the other server. Nominatim
uses a custom normalization library that needs to be made accessible to the
PostgreSQL server. This section explains how to set up the normalization
library.

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
the nomrmalization library in `build/module/nominatim.so`. Copy the file to
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
to follow the [standard instructions for importing](/admin/Import).

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
    with `${UPDATEFILE} --import-file ${UPDATEDIR}/tmp/combined.osm.pbf 2>&1`.

### Setting up multiple regions

Run the following command from your Nominatim directory after configuring the file.

    bash ./utils/import_multiple_regions.sh

!!! danger "Important"
        This file uses osmium-tool. It must be installed before executing the import script.
        Installation instructions can be found [here](https://osmcode.org/osmium-tool/manual.html#installation).

## Updating multiple regions

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

## Verification and further setup

Instructions for import verification and other details like importing Wikidata can be found in the [import section](Import.md)


# Customization of the Database

This section explains in detail how to configure a Nominatim import and
the various means to use external data.

## External postcode data

Nominatim creates a table of known postcode centroids during import. This table
is used for searches of postcodes and for adding postcodes to places where the
OSM data does not provide one. These postcode centroids are mainly computed
from the OSM data itself. In addition, Nominatim supports reading postcode
information from an external CSV file, to supplement the postcodes that are
missing in OSM.

To enable external postcode support, simply put one CSV file per country into
your project directory and name it `<CC>_postcodes.csv`. `<CC>` must be the
two-letter country code for which to apply the file. The file may also be
gzipped. Then it must be called `<CC>_postcodes.csv.gz`.

The CSV file must use commas as a delimiter and have a header line. Nominatim
expects three columns to be present: `postcode`, `lat` and `lon`. All other
columns are ignored. `lon` and `lat` must describe the x and y coordinates of the
postcode centroids in WGS84.

The postcode files are loaded only when there is data for the given country
in your database. For example, if there is a `us_postcodes.csv` file in your
project directory but you import only an excerpt of Italy, then the US postcodes
will simply be ignored.

As a rule, the external postcode data should be put into the project directory
**before** starting the initial import. Still, you can add, remove and update the
external postcode data at any time. Simply
run:

```
nominatim refresh --postcodes
```

to make the changes visible in your database. Be aware, however, that the changes
only have an immediate effect on searches for postcodes. Postcodes that were
added to places are only updated, when they are reindexed. That usually happens
only during replication updates.

## Installing Tiger housenumber data for the US

Nominatim is able to use the official [TIGER](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
address set to complement the OSM house number data in the US. You can add
TIGER data to your own Nominatim instance by following these steps. The
entire US adds about 10GB to your database.

  1. Get preprocessed TIGER 2020 data:

        cd $PROJECT_DIR
        wget https://nominatim.org/data/tiger2020-nominatim-preprocessed.csv.tar.gz

  2. Import the data into your Nominatim database:

        nominatim add-data --tiger-data tiger2020-nominatim-preprocessed.csv.tar.gz

  3. Enable use of the Tiger data in your `.env` by adding:

        echo NOMINATIM_USE_US_TIGER_DATA=yes >> .env

  4. Apply the new settings:

        nominatim refresh --functions


See the [developer's guide](../develop/data-sources.md#us-census-tiger) for more
information on how the data got preprocessed.

## Special phrases import

As described in the [Importation chapter](Import.md), it is possible to
import special phrases from the wiki with the following command:

```sh
nominatim special-phrases --import-from-wiki
```

But, it is also possible to import some phrases from a csv file. 
To do so, you have access to the following command:

```sh
nominatim special-phrases --import-from-csv <csv file>
```

Note that the 2 previous import commands will update the phrases from your database.
This means that if you import some phrases from a csv file, only the phrases
present in the csv file will be kept into the database. All other phrases will
be removed.

If you want to only add new phrases and not update the other ones you can add
the argument `--no-replace` to the import command. For example:

```sh
nominatim special-phrases --import-from-csv <csv file> --no-replace
```

This will add the phrases present in the csv file into the database without
removing the other ones.

# External postcode data

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

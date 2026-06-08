# External postcode data

Nominatim creates a table of known postcode centroids and geometries during import.
This table is used for searches of postcodes and for adding postcodes to places where
the OSM data does not provide one. These postcode centroids are mainly computed
from the OSM data itself. In addition, Nominatim supports reading postcode information
from external files to supplement the postcodes that are missing in OSM.

## Supported file formats

Nominatim supports 2 data formats for external import:

### JSONL format

The JSONL format may contain the postcode data along with a POLYGON or MULTIPOLYGON geometry
of the postcode area. To enable external postcode support, put one file per country into
your project directory and name it `<CC>_postcodes_geometry.<ext>`. `<CC>` must be the
two-letter country code for which to apply the file. File type may be either `.jsonl` or
`.jsonl.gz` (gzip compressed). The file must be in UTF-8 encoding and contain one JSON object
per line with the following structure:

#### GeoJSON Feature

A standard [RFC7946](https://geojson.org) GeoJSON Feature object.

* `geometry`: (required) A GeoJSON geometry (Polygon/MultiPolygon).
* `properties`: (required) An object containing:
  * `postcode`: (required) The postcode string.
  * `lat`, `lon`: (optional) Coordinates for the centroid. If not provided, the centroid
  is computed from the geometry.

### CSV format

To enable external postcode support, put one file per country into
your project directory and name it `<CC>_postcodes.<ext>`. `<CC>` must be the
two-letter country code for which to apply the file. File type may be either `.csv` or `.csv.gz`
(gzip compressed). The CSV file must use commas as a delimiter and have a header line. Nominatim
expects three columns to be present: `postcode`, `lat` and `lon`. All other columns are ignored.
`lon` and `lat` must describe the x and y coordinates of the postcode centroids in WGS84.

The postcode area is assumed to be in a buffer around the centroid (typically 5km).

## Usage

As a rule, the external postcode data should be put into the project directory
**before** starting the initial import. Still, you can add, remove and update the
external postcode data at any time. Simply run:

```
nominatim refresh --postcodes
```

to make the changes visible in your database. Be aware, however, that the changes
only have an immediate effect on searches for postcodes. Postcodes that were
added to places are only updated, when they are reindexed. That usually happens
only during replication updates.

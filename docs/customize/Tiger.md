# Installing TIGER housenumber data for the US

Nominatim is able to use the official [TIGER](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
address set to complement the OSM house number data in the US. You can add
TIGER data to your own Nominatim instance by following these steps. The
entire US adds about 10GB to your database.

  1. Get preprocessed TIGER data:

        cd $PROJECT_DIR
        wget https://nominatim.org/data/tiger-nominatim-preprocessed-latest.csv.tar.gz

  2. Import the data into your Nominatim database:

        nominatim add-data --tiger-data tiger-nominatim-preprocessed-latest.csv.tar.gz

  3. Enable use of the Tiger data in your existing `.env` file by adding:

        echo NOMINATIM_USE_US_TIGER_DATA=yes >> .env

  4. Apply the new settings:

        nominatim refresh --functions --website


## Importing only part of the US

If your database covers only part of the US, you can speed up the import by
cutting the TIGER data down to that area first. Use the script
`tiger_create_extract.py` from the
[TIGER-data project](https://github.com/osm-search/TIGER-data). It needs
nothing but Python 3. Select states by abbreviation or FIPS code (`--states`),
a bounding box (`--bbox`), or both:

    python3 tiger_create_extract.py --states NY,NJ \
        tiger-nominatim-preprocessed-latest.csv.tar.gz tiger-ny-nj/

The result is a directory of CSV files. Use it in step 2 in place of the
archive:

    nominatim add-data --tiger-data tiger-ny-nj/

Run `python3 tiger_create_extract.py --help` for more examples.


See the [TIGER-data project](https://github.com/osm-search/TIGER-data) for more
information on how the data got preprocessed.


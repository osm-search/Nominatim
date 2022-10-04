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

  3. Enable use of the Tiger data in your `.env` by adding:

        echo NOMINATIM_USE_US_TIGER_DATA=yes >> .env

  4. Apply the new settings:

        nominatim refresh --functions


See the [TIGER-data project](https://github.com/osm-search/TIGER-data) for more
information on how the data got preprocessed.


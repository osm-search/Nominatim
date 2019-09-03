# US TIGER address data

Convert [TIGER](https://www.census.gov/geo/maps-data/data/tiger.html)/Line dataset of the US Census Bureau to SQL files which can be imported by Nominatim. The created tables in the Nominatim database are separate from OpenStreetMap tables and get queried at search time separately.

The dataset gets updated once per year. Downloading is prone to be slow (can take a full day) and converting them can take hours as well.

Replace '2019' with the current year throughout.

  1. Install the GDAL library and python bindings and the unzip tool

        # Ubuntu:
        sudo apt-get install python3-gdal unzip

  2. Get the TIGER 2019 data. You will need the EDGES files
     (3,233 zip files, 11GB total).

         wget -r ftp://ftp2.census.gov/geo/tiger/TIGER2019/EDGES/

  3. Convert the data into SQL statements. Adjust the file paths in the scripts as needed

        cd data-sources/us-tiger
        ./convert.sh <input-path> <output-path>

  4. Maybe: package the created files
  
        tar -czf tiger2019-nominatim-preprocessed.tar.gz tiger

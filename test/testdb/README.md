Creating the test database
==========================

The official test dataset is derived from the 160725 planet. Newer
planets are likely to work as well but you may see isolated test
failures where the data has changed. To recreate the input data
for the test database run:

    wget http://free.nchc.org.tw/osm.planet/pbf/planet-160725.osm.pbf
    osmconvert planet-160725.osm.pbf -B=testdb.polys -o=testdb.pbf

Before importing make sure to add the following to your local settings:

    @define('CONST_Database_DSN', 'pgsql://@/test_api_nominatim');
    @define('CONST_Wikipedia_Data_Path', CONST_BasePath.'/test/testdb');

## Introduction

This report is the documentation of Nominatim's Google Summer of Code 2022 project — "Importance By OSM views", which is about enhancing Nominatim’s search results ranking using OSM views data. To have a background understanding of the project, you can check the overview of the project [here](https://www.openstreetmap.org/user/tareqpi/diary/399231) followed by the project’s first phase [here](https://www.openstreetmap.org/user/tareqpi/diary/399655).


## Second Phase Goals

Below are the goals of the second and final phase of this project.

1. Enhancing the performance of the import functionality
2. Investigating and developing the importance value computation algorithm based on the views count of each tile
3. Verifying the results of integrating the OSM views into the current importance computation


## Import Functionality Performance Enhancements

The performance of the import functionality significantly improved compared to how it was in the first phase of this project. The original import technique that was implemented in the first phase was inefficient in terms of time (over 3 hours) and space (over 4 GB) and that is because there was a logical flaw that was later identified. The [GeoTIFF](https://en.wikipedia.org/wiki/GeoTIFF) file that is used to import the OSM views data is multi-dimensional which means that the GeoTIFF has different zoom levels and in each zoom level there is a different set of data as shown in the figure below.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1rFCLxEoOb2ckIfiss1fUkHEr_Fl0bRbf">
  <p>Fig.1 - Output of `identify` command</p>
</div>


[Raster2pgsql](https://postgis.net/docs/using_raster_dataman.html#RT_Raster_Loader), which is the tool used to import the raster, was importing all the zoom levels at once which cluttered the raster table with all the unnecessary tiles from all the zoom levels and resulted in the import process taking so much time and space. Multi-dimensional GeoTIFF files have overviews which, in the case of this project, are the zoom levels for the map. The figure below shows the overviews that are embedded into the GeoTIFF file.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1EDDRtuVrpSKxfsJQb3_pLIHYtme1kuTs">
  <p>Fig.2 - Output of `gdalinfo` command</p>
</div>


[Gdalwarp](https://gdal.org/programs/gdalwarp.html), which is a raster warping, reprojection, and mosaicing tool, is added to be programmatically called to create a compressed, temporary version of the original GeoTIFF file that has the needed Spatial Reference Identifier ([SRID](https://en.wikipedia.org/wiki/Spatial_reference_system)) as well as one of the overview levels which corresponds to a zoom level so that it can be correctly imported to Nominatim’s database. It takes around 15 seconds to reproject and create the temporary GeoTIFF file with a specific zoom level. The temporary GeoTIFF file will be deleted automatically after its data has been imported to the database. Additionally, raster2pgsql’s option to use the COPY statement is used instead of the INSERT statement to speed up the import process. Furthermore, the tile size is now bigger (256x256) than what it was previously (100x100) in the first phase of the project. Below is the portion of the code responsible for the GeoTIFF import process.


```python
            # -ovr: 6 -> zoom 12, 5 -> zoom 13, 4 -> zoom 14, 3 -> zoom 15
            reproject_geotiff = f"gdalwarp -q -multi -ovr 3 -overwrite \
                -co COMPRESS=LZW -tr 0.01 0.01 -t_srs EPSG:4326 {datafile} raster2import.tiff"
            subprocess.run(["/bin/bash", "-c" , reproject_geotiff], check=True)

            tile_size = 256
            import_geotiff = f"raster2pgsql -I -C -Y -t {tile_size}x{tile_size} raster2import.tiff \
                public.osm_views | psql {dsn} > /dev/null"
            subprocess.run(["/bin/bash", "-c" , import_geotiff], check=True)

            cleanup = "rm raster2import.tiff"
            subprocess.run(["/bin/bash", "-c" , cleanup], check=True)

```
<br/>

As shown in the [table](https://wiki.openstreetmap.org/wiki/Zoom_levels) below, based on the areas that each zoom level can represent, the most suitable tile zoom levels to use are zoom levels 12 to 15.


<div align="center">
  <p>Table 1 - Information About Map Zoom Levels</p>
  <img src="https://drive.google.com/uc?export=view&id=1fQeeA6XC1eE18njkHfe5Xre4LWH1DopI">
</div>

<br/><br/>

Furthermore, the table below are performance measurement results of the selected zoom levels of the GeoTIFF file. The server used to conduct the performance measurements has 8 core AMD Ryzen™ 7 3700X, 64GB RAM, 1TB NVMe disk (900GB usable, 850GB free), running Ubuntu 22.04 LTS.

<div align="center">
  <p>Table 2 - GeoTIFF Peformance Results in Different Zoom Levels</p>

|Zoom Level|Zoom 12|Zoom 13|Zoom 14|Zoom 15|
|:---|:---:|:---:|:---:|:---:|
|Average Import Time|~ 8 minutes|~ 8 minutes|~ 8 minutes|~ 8 minutes|
|Average Query Time (10,000 rows per query)|~ 520.512 ms|~ 609.836 ms|~ 975.231 ms|~ 1677.699 ms|
|Table Size|55 MB|58 MB|64 MB|74 MB|
|Number of Rows|9447|9447|9447|9447|

</div>


## Data Normalization of OSM Views

Data normalization is the process of preparing and transforming the numeric values so that they use a common scale. The imported OSM views numbers need to be normalized so that they can be correctly integrated into the computation of the importance scores. The scale that is used for the OSM views data ranges from 0 to 1. Below are the normalization techniques that have been tested.


### 1) Min-Max Normalization

The min-max normalization technique takes the difference between the number that needs to be normalized and the minimum value found in the dataset, to divide it by the difference between the maximum and the minimum values in the dataset as shown below. This normalization technique however cannot be used for this project as it has a drawback due to it being very sensitive to outliers. The maximum number of views is very huge compared to most of the other tile view counts which mean that the division will usually yield a very tiny number that is close to zero (example: 40 divided by 4,000,000 = 0.00001).

$$\LARGE views_{norm} = \frac{views_{i} - min(views)}{max(views) - min(views)}$$

### 2) Logarithmic Transformation

The second approach to scale the numbers so that they be in the range of 0 to 1 is to use the logarithmic transformation. This approach has a logarithmic growth as opposed to the min-max normalization which has a linear growth. The logarithmic transformation takes the log function of the number that needs to be normalized and then divides it by the log function of the maximum number in the dataset. Furthermore, this technique is not affected by the outliers as the min-max normalization, therefore it is more suitable to be used in this project than the min-max normalization.

$$\LARGE views_{norm} = \frac{\log(views_{i})}{\log(max(views))}$$

Below is a visualization of the logarithmic transformation where the maximum number of views is set to 5 which, compared to the actual OSM views, is a very small number that is only chosen so that the graph below can be easily read. The X-axis represents the number of views and the Y-axis contains the valid range of normalization which is from 0 to 1. The normalized value (Y-axis) increases as the number of views (X-axis) gets closer to the maximum views count.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1YWA8j4haQOKuVa8eqo-iT6XvrrWDay-I">
  <p>Fig.3 - Visualization of The Logarithmic Transformation</p>
</div>


## Computation of the Importance Score

Nominatim currently uses the wiki importance data solely to set the importance score for the places that are important enough to have a Wikipedia article. Now that the OSM views data is in the database, it will be used as a secondary parameter with the wiki data being the primary parameter to compute the importance scores for all places. The new importance score consists of the wiki importance data with the addition of the normalized OSM views to the wiki importance values. OSM views importance data has a weightage of 35% and the wiki importance data has a weightage of 65%. These percentages are set as initial values that need to be later reviewed.

$$\LARGE \text{Importance} = (\text{Wiki}\times0.65) + (\text{OSM Views}\times0.35)$$

## Integrating OSM Views Into Importance Score Computation

The new additions that are proposed to be added into Nominatim’s codebase are tested to understand how the OSM views data alter and enhance the accuracy of the importance score computation for each place. Because testing with a database that has a full planet import takes a significant amount of time, a smaller database is created that contains a subset of the OSM data to faster test the new importance computation. The chosen data subset that is used is [Latvia’s OSM data](https://download.geofabrik.de/europe/latvia.html) which is currently 96 MB in size (compared to 58 GB for the whole planet). Furthermore, the [wiki importance data](https://www.nominatim.org/data/wikimedia-importance.sql.gz) and the GeoTIFF file that has the OSM views data are downloaded to be used for the places’ importance score computation. The first step is to import Latvia’s OSM data and wiki importance data into Nominatim’s database. This is done by putting the Latvia's OSM file and the wiki importance file into the project directory to initiate the import process using the command below.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1oVCtT4VHE1gWKunfXD5HUKxx7YXzoxQf">
  <p>Fig.4 - Importing Latvia’s Osm File and Wikipedia Importance Data</p>
</div>


After the wikipedia importance data and Latvia’s OSM file are imported into the database, a new table called `place_wiki_importance` is created to preserve the importance scores that are based on the wiki data. It is done by extracting the wikipedia importance information from the `placex` table. These information are `place_id`, and the wiki importance score with their wikipedia articles. As explained before, the wiki data importance score is multiplied by 0.65 in `importance.sql` which is the file responsible for calculating the importance score. The SQL query below creates the `place_wiki_importance` table.

```SQL
CREATE TABLE place_wiki_importance AS (
	SELECT place_id, importance, wikipedia
	FROM placex
	WHERE wikipedia IS NOT NULL
);
```

After the wiki data is copied to another table to be used later, the GeoTIFF file is then cropped to create a smaller version of the file that only contains the OSM views data of Latvia. Gdalwarp is used in order to crop a region from the original GeoTIFF file. This is done by downloading a zip file that contains a [shapefile](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries-2) of the countries in which the zip file is extracted and cut to use Latvia’s polygon with the gdalwarp command line to cut the GeoTIFF file as shown below. The polygons are simplified and do not exactly match with the OSM map, however, it is still good enough for the purpose of analyzing the results of the importance score computation. In addition to extracting the correct shape of the GeoTIFF file, an overview level must be extracted where each overview level equates to a different zoom level. Zoom levels 12, 13, 14, and 15 correspond in the GeoTIFF file to overview levels 6, 5, 4, and 3 respectively. Furthermore, the extracted raster is reprojected to have the SRID of 4326 so that it matches the SRID of the centroids of the places in `placex` table.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1TBrgjY1fzew4Rs82WAql99RbHBrAbhX_">
  <p>Fig.5 - Cropping and Reprojecting the GeoTIFF File</p>
</div>


Now that Latvia’s extract of the original GeoTIFF file is ready, the cropped GeoTIFF file is put into the project’s directory and then the code portion of computing the wiki importance score in the function `compute_importance` in `importance.sql` is commented out so that the new importance score is computed only using the OSM views data. The next step is running Nominatim’s refresh function to import the GeoTIFF extract into a raster table and then compute the OSM views importance values and put them in the table `placex` using the command below.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1-FEnNfJytYEYIzpudYje5A_aIsoHFN_B">
  <p>Fig.6 - Nominatim Refreshing OSM Views Data and Importance Score</p>
</div>


This is the correct way of refreshing the OSM views importance values when running Nominatim normally, however, when testing the computation of the importance score using a GeoTIFF extract, the maximum views value is limited to the views numbers inside that GeoTIFF extract. Therefore, the code portion of retrieving the maximum views value is disabled and a hardcoded maximum value is set in the OSM views normalization function. The maximum views value is retrieved from the log file that is found in the [tile server](https://planet.openstreetmap.org/tile_logs). A simple python script that is shown below reads through that log file and returns the maximum views values for the tiles of zoom levels 12 to 15.

```python
#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("filename", help = "Name of the file that will be read from")
args = parser.parse_args()

max_views = {'zoom_12': {'tile': '', 'views': 0},
             'zoom_13': {'tile': '', 'views': 0},
             'zoom_14': {'tile': '', 'views': 0},
             'zoom_15': {'tile': '', 'views': 0}}

file = open(args.filename, 'r')
lines = file.readlines()

for line in lines:
    splitline=line.split(' ',2)
    tile=splitline[0].split('/',4)
    if (tile[0] == '12'):
        views = int(splitline[1])
        if (views > max_views['zoom_12']['views']):
            max_views['zoom_12']['views'] = views
            max_views['zoom_12']['tile'] = f'({tile[1]}, {tile[2]})'
    elif (tile[0] == '13'):
        views = int(splitline[1])
        if (views > max_views['zoom_13']['views']):
            max_views['zoom_13']['views'] = views
            max_views['zoom_13']['tile'] = f'({tile[1]}, {tile[2]})'
    elif (tile[0] == '14'):
        views = int(splitline[1])
        if (views > max_views['zoom_14']['views']):
            max_views['zoom_14']['views'] = views
            max_views['zoom_14']['tile'] = f'({tile[1]}, {tile[2]})'
    elif (tile[0] == '15'):
        views = int(splitline[1])
        if (views > max_views['zoom_15']['views']):
            max_views['zoom_15']['views'] = views
            max_views['zoom_15']['tile'] = f'({tile[1]}, {tile[2]})'

for k, v in max_views.items():
    print(k, v)

```

The maximum views values of the chosen zoom levels currently is shown in the table below. Before refreshing the OSM views data and recomputing the importance score based on each selected zoom level, the hardcoded maximum views value in the normalization function must be changed accordingly.

<div align="center">
  <p>Table 3 - Maximum Views Count of Different Zoom levels</p>

|Zoom Level|Max OSM Views Count|
|:---:|:---:|
|12|2,949,997|
|13|271,203|
|14|455,542|
|15|418,428|

</div>
<br/>

After the raster table `osm_views` is created from the cropped GeoTIFF file, the data inside that table is used to get the raw OSM view numbers. This is done by creating another table that contains the place_id’s from the `placex` table as well as the corresponding view numbers which are extracted from finding a raster in the raster table that intersects with the places’ centroids. The SQL query below shows the creation of the `place_views` table.


```SQL
CREATE TABLE place_views_z12 AS (
	SELECT placex.place_id, ST_Value(osm_views.rast, centroid)::BIGINT AS views_z12
	FROM osm_views, placex
	WHERE ST_Intersects(ST_ConvexHull(osm_views.rast), centroid)
);
```


Once the raw OSM view numbers are extracted and put into the new `place_views` table, another table, called `place_importance`, is created which contains all the necessary information to create graphs that show the relationship of the parameters that contribute to the final importance score. The `place_importance` table has places' wikipedia articles with their wiki importance scores, their raw OSM views with their OSM views importance scores, and their total combined importance score. The SQL query below shows the creation of the `place_importance` table.


```SQL
CREATE TABLE place_importance_z12 AS (
	SELECT placex.place_id,
	(placex.importance + COALESCE(place_wiki_importance.importance, 0)) AS total_importance,
	place_wiki_importance.importance AS wiki_importance,
	place_wiki_importance.wikipedia,
	placex.importance AS osm_views_importance,
	place_views_z12.views_z12 AS views
	FROM placex
	LEFT JOIN place_wiki_importance ON placex.place_id = place_wiki_importance.place_id
	JOIN place_views_z12 ON placex.place_id = place_views_z12.place_id
);
```


After the initial `place_importance` table of one of the zoom levels is created and filled with the correct data, the steps needed to create the `place_importance` tables of the other zoom levels become fewer. The step of importing the wiki data is skipped since that data is already available in the `place_wiki_importance` table. The table below is an example of the `place_importance` table for zoom level 15. `total_importance` is the final importance computation which is the sum of `wiki_importance` data (65%) and `osm_views_importance` data (35%).


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=197yEIXNaYrYN43-kPsiG-diNxoZz-nPr">
  <p>Fig.7 - `place_importance` Table</p>
</div>


## Visualizing the Results

Now that the `place_importance` tables are created for each zoom level, the data in each of these tables are visualized. There are two sets of graphs that are created: correlation graphs between the two parameters used in the importance computation formula and the visualizations of the OSM views normalization process. The graphs are created with [Grafana](https://grafana.com/oss/grafana) in which the data source is configured to be Nominatim’s database which holds the `place_importance` table of each zoom level. Furthermore, in order to create the graphs, a plugin called [scatter](https://grafana.com/grafana/plugins/michaeldmoore-scatter-panel) is installed and used with Grafana.

The visualization of the OSM views data normalization is shown below for zoom levels 12 to 15. The graphs are created by querying the `place_importance` table where the raw OSM views (up to 10,000 views) and the normalized forms (`osm_views_importance`) are retrieved to be displayed in the graph in which they are represented on the x-axis and the y-axis respectively. Furthermore, the numbers in the `osm_views_importance` column are divided by 0.35 to cancel the multiplication that happened previously when processing the OSM views importance data in the computation of the final importance score.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=15EMqFjJerrvDGwj5qAaiXZFcgL3rDz23">
  <p>Fig.8 - OSM Views Normalization (zoom 12)</p>
</div>

<br/><br/><br/><br/>

<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1LZkR4C_8hzTJA8WC1iMb3p7lr0QUJ5AL">
  <p>Fig.9 - OSM Views Normalization (zoom 13)</p>
</div>

<br/><br/><br/><br/>

<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1T4ltjlx9hBTRexZVhcIC-X_Sgccbxe0I">
  <p>Fig.10 - OSM Views Normalization (zoom 14)</p>
</div>

<br/><br/><br/><br/>

<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=19ljb5lB7ptWAzN8GzDkcht_lOebEsAJc">
  <p>Fig.11 - OSM Views Normalization (zoom 15)</p>
</div>

<br/><br/><br/><br/>

The correlation graphs between the OSM views importance data and the wiki importance data of zoom levels 12 to 15 are shown below. The graphs are created by querying the data in `wiki_importance` and the data in `osm_views_importance` from the table `place_importance` for each zoom level. Additionally, `wiki_importance` and `osm_views_importance` are divided by 0.65 and 0.35 respectively so they cancel the weightage that is set previously in the final importance score computation so both of them are graphed using the same scale (0 to 1).


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1lQn4rmO7XY1SKIigpwuWp_oW-zjO04z6">
  <p>Fig.12 - Correlation Graph (zoom 12)</p>
</div>

<br/><br/><br/><br/>

<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1n6TPt4WVaEvoMo_ia6nb5aXGzfNzZ4vz">
  <p>Fig.13 - Correlation Graph (zoom 13)</p>
</div>

<br/><br/><br/><br/>

<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=16-wmeBysfNEEzTLfAopyhVB2GESI2c8Q">
  <p>Fig.14 - Correlation Graph (zoom 14)</p>
</div>

<br/><br/><br/><br/>

<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1KeC2DTKsAvD2EEdN_a97x3FMZAvpXtnY">
  <p>Fig.15 - Correlation Graph (zoom 15)</p>
</div>

<br/><br/><br/><br/>

The table below shows the correlation coefficient for each of the zoom levels tested using Latvia’s GeoTIFF extract. The correlation between the wiki importance data and the OSM views importance data indicates a weak correlation at zoom levels 12 to 15.

<div align="center">
  <p>Table 4 - Zoom Levels Correlation Coefficients</p>

|Zoom Level|Correlation Coefficient|
|:---:|:---:|
|12|0.242|
|13|0.257|
|14|0.262|
|15|0.261|

</div>

## Discussion of the Results

As seen from the correlation graphs, there is a weak correlation between the OSM views importance data and the wiki importance data. It is a strange outcome since it was expected that these parameters have a strong correlation since they contribute to the computation of the new importance score. This could be for a number of reasons which need further testing to be verified.


### 1) Zoom Level Bias

Since each zoom level is essentially a different tile in the tile log server, the OSM views data of each zoom level will favor places of a certain size corresponding to that zoom level. For example, users will not need to zoom in that much to view a big place like a city, so the tiles that have a high zoom level will not be served by the server thereby the view count for the high zoom level tiles does not increase. The image below shows several places having different view counts depending on the zoom level. A solution to this potential problem would be further enhancing the import process of the GeoTIFF file so that it includes the OSM views data of multiple zoom levels in its importance computation. Each zoom level data can have a different weight in the computation of the final importance score so that all places have holistic importance scores that truly reflect the importance of each place regardless of the place size and the zoom level used to view that place.


<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1ZBmcL_ZspNOViVG9bRvg07XP5YPRB7jH">
  <p>Fig.16 - Places Views in Different Zoom Levels</p>
</div>


### 2) Unusual Spikes in OSM Views Numbers

Another potential reason for the weak correlation is that OpenStreetMap is integrated into several theme-specific applications in which users of one of those applications drive the view numbers of places of a certain theme that match that of the application. This causes skewness in the data and the GeoTIFF file containing inaccurate data which needs to be cleaned.


### 3) Trending Places vs Importance of Places

An alternative explanation for the weak correlation is that the metric used for calculating the wiki importance score for each place is simply different from what the OSM views data actually represents. The logs of the tile server contain the number of requests per tile in a given 24-hour UTC day and the GeoTIFF file is created using the set of logs for one week. This shows that the OSM views data is just a snapshot of what is trending at a specific time range. Below is a figure that shows the previously shared python script extracting the maximum OSM views numbers from log files of ten consecutive days. The maximum OSM views numbers of each zoom level is fluctuating depending on the day.

<div align="center">
  <img src="https://drive.google.com/uc?export=view&id=1zKBvZVMXCfgrjg5Jk1y0Vw4XFPtis7qd">
  <p>Fig.17 - Fluctuation in OSM Maximum Views Numbers During 10-Day Period Time</p>
</div>

The historic importance of a place does not necessarily mean that the place is interesting enough for the users to view it, but rather, the users want to view places that are currently trending such as a place that has been opened recently, or a place that hosts an important sporting event. In a way, this means that adding the OSM views data actually enhances the importance score computation of a place in a different dimension that is not considered in the wiki importance data. However, if that is the case, then the OSM importance data should be limited to a high degree where it does not negatively affect the ranking of places because of the OSM views fluctuations.

## Acknowledgments

I would like to thank my mentors, Sarah Hoffman ([@lonvia](https://www.openstreetmap.org/user/lonvia)) and Marc Tobias ([@mtmail](https://www.openstreetmap.org/user/mtmail)), for their guidance and support throughout the implementation of this project. I would also like to thank Paul Norman ([@pnorman](https://www.openstreetmap.org/user/pnorman)) for his comment and the discussion I had with him afterward that shaped the implementation of this project. I would also like to thank [OpenCage](https://opencagedata.com) for providing me with the server to work with on this project. I had a great learning experience and I am thankful to Google Summer of Code and to the OpenStreetMap Foundation for this opportunity.

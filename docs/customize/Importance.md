## Importance

Search requests can yield multiple results which match equally well with
the original query. In such case Nominatim needs to order the results
according to a different criterion: importance. This is a measure for how
likely it is that a user will search for a given place. This section explains
the sources Nominatim uses for computing importance of a place and how to
customize them.

### How importance is computed

The main value for importance is derived from page ranking values for Wikipedia
pages for a place. For places that do not have their own
Wikipedia page, a formula is used that derives a static importance from the
places [search rank](../customize/Ranking#search-rank).

In a second step, a secondary importance value is added which is meant to
represent how well-known the general area is where the place is located. It
functions as a tie-breaker between places with very similar primary
importance values.

nominatim.org has preprocessed importance tables for the
[primary Wikipedia rankings](https://nominatim.org/data/wikimedia-importance.sql.gz)
and for a secondary importance based on the number of tile views on openstreetmap.org.

### Customizing secondary importance

The secondary importance is implemented as a simple
[Postgis raster](https://postgis.net/docs/raster.html) table, where Nominatim
looks up the value for the coordinates of the centroid of a place. You can
provide your own secondary importance raster in form of an SQL file named
`secondary_importance.sql.gz` in your project directory.

The SQL file needs to drop and (re)create a table `secondary_importance` which
must as a minimum contain a column `rast` of type `raster`. The raster must
be in EPSG:4326 and contain 16bit unsigned ints
(`raster_constraint_pixel_types(rast) = '{16BUI}'). Any other columns in the
table will be ignored. You must furthermore create an index as follows:

```
CREATE INDEX ON secondary_importance USING gist(ST_ConvexHull(gist))
```

The following raster2pgsql command will create a table that conforms to
the requirements:

```
raster2pgsql -I -C -Y -d -t 128x128 input.tiff public.secondary_importance
```

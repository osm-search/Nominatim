# OSM Data Import

OSM data is initially imported using [osm2pgsql](https://osm2pgsql.org).
Nominatim uses its own data output style 'gazetteer', which differs from the
output style created for map rendering.

## Database Layout

The gazetteer style produces a single table `place` with the following rows:

 * `osm_type` - kind of OSM object (**N** - node, **W** - way, **R** - relation)
 * `osm_id` - original OSM ID
 * `class` - key of principal tag defining the object type
 * `type` - value of principal tag defining the object type
 * `name` - collection of tags that contain a name or reference
 * `admin_level` - numerical value of the tagged administrative level
 * `address` - collection of tags defining the address of an object
 * `extratags` - collection of additional interesting tags that are not
                 directly relevant for searching
 * `geometry` - geometry of the object (in WGS84)

A single OSM object may appear multiple times in this table when it is tagged
with multiple tags that may constitute a principal tag. Take for example a
motorway bridge. In OSM, this would be a way which is tagged with
`highway=motorway` and `bridge=yes`. This way would appear in the `place` table
once with `class` of `highway` and once with a `class` of `bridge`. Thus the
*unique key* for `place` is (`osm_type`, `osm_id`, `class`).

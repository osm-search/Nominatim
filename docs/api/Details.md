# Place details

Show all details about a single place saved in the database.

!!! warning
    The details page exists for debugging only. You may not use it in scripts
    or to automatically query details about a result.
    See [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).


## Parameters

The details API supports the following two request formats:

``` xml
https://nominatim.openstreetmap.org/details?osmtype=[N|W|R]&osmid=<value>&class=<value>
```

`osmtype` and `osmid` are required parameters. The type is one of node (N), way (W)
or relation (R). The id must be a number. The `class` parameter is optional and
allows to distinguish between entries, when the corresponding OSM object has more
than one main tag. For example, when a place is tagged with `tourism=hotel` and
`amenity=restaurant`, there will be two place entries in Nominatim, one for a
restaurant, one for a hotel. You need to specify `class=tourism` or `class=amentity`
to get exactly the one you want. If there are multiple places in the database
but the `class` parameter is left out, then one of the places will be chosen
at random and displayed.

``` xml
https://nominatim.openstreetmap.org/details?place_id=<value>
```

Place IDs are assigned sequentially during Nominatim data import. The ID
for a place is different between Nominatim installation (servers) and
changes when data gets reimported. Therefore it cannot be used as
a permanent id and shouldn't be used in bug reports.


Additional optional parameters are explained below.

### Output format

* `json_callback=<string>`

Wrap JSON output in a callback function (JSONP) i.e. `<string>(<json>)`.

* `pretty=[0|1]`

Add indentation to make it more human-readable. (Default: 0)


### Output details

* `addressdetails=[0|1]`

Include a breakdown of the address into elements. (Default: 0)

* `keywords=[0|1]`

Include a list of name keywords and address keywords (word ids). (Default: 0)

* `linkedplaces=[0|1]`

Include a details of places that are linked with this one. Places get linked
together when they are different forms of the same physical object. Nominatim
links two kinds of objects together: place nodes get linked with the
corresponding administrative boundaries. Waterway relations get linked together with their
members.
(Default: 1)

* `hierarchy=[0|1]`

Include details of places lower in the address hierarchy. (Default: 0)

* `group_hierarchy=[0|1]`

For JSON output will group the places by type. (Default: 0)

* `polygon_geojson=[0|1]`

Include geometry of result. (Default: 0)

### Language of results

* `accept-language=<browser language string>`

Preferred language order for showing result, overrides the value
specified in the "Accept-Language" HTTP header.
Either use a standard RFC2616 accept-language string or a simple
comma-separated list of language codes.


## Examples

##### JSON

[https://nominatim.openstreetmap.org/details.php?osmtype=W&osmid=38210407&format=json](https://nominatim.openstreetmap.org/details.php?osmtype=W&osmid=38210407&format=json)


```json
{
  "place_id": 85993608,
  "parent_place_id": 72765313,
  "osm_type": "W",
  "osm_id": 38210407,
  "category": "place",
  "type": "square",
  "admin_level": "15",
  "localname": "Pariser Platz",
  "names": {
    "name": "Pariser Platz",
    "name:be": "Парыжская плошча",
    "name:de": "Pariser Platz",
    "name:es": "Plaza de París",
    "name:he": "פאריזר פלאץ",
    "name:ko": "파리저 광장",
    "name:la": "Forum Parisinum",
    "name:ru": "Парижская площадь",
    "name:uk": "Паризька площа",
    "name:zh": "巴黎廣場"
  },
  "addresstags": {
    "postcode": "10117"
  },
  "housenumber": null,
  "calculated_postcode": "10117",
  "country_code": "de",
  "indexed_date": "2018-08-18T17:02:45+00:00",
  "importance": 0.339401620591472,
  "calculated_importance": 0.339401620591472,
  "extratags": {
    "wikidata": "Q156716",
    "wikipedia": "de:Pariser Platz"
  },
  "calculated_wikipedia": "de:Pariser_Platz",
  "rank_address": 30,
  "rank_search": 30,
  "isarea": true,
  "centroid": {
    "type": "Point",
    "coordinates": [
      13.3786822618517,
      52.5163654
    ]
  },
  "geometry": {
    "type": "Point",
    "coordinates": [
      13.3786822618517,
      52.5163654
    ]
  }
}
```

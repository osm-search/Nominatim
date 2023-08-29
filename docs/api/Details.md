# Place details

Show all details about a single place saved in the database.

This API endpoint is meant for visual inspection of the data in the database,
mainly together with [Nominatim-UI](https://github.com/osm-search/nominatim-ui/).
The parameters of the endpoint and the output may change occasionally between
versions of Nominatim. Do not rely on the output in scripts or applications.

!!! warning
    The details endpoint at https://nominatim.openstreetmap.org
    may not used in scripts or bots at all.
    See [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).



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

!!! danger "Deprecation warning"
    The API can also be used with the URL
    `https://nominatim.openstreetmap.org/details.php`. This is now deprecated
    and will be removed in future versions.


## Parameters

This section lists additional optional parameters.

### Output format

| Parameter | Value | Default |
|-----------| ----- | ------- |
| json_callback | function name | _unset_ |

When set, then JSON output will be wrapped in a callback function with
the given name. See [JSONP](https://en.wikipedia.org/wiki/JSONP) for more
information.

| Parameter | Value | Default |
|-----------| ----- | ------- |
| pretty    | 0 or 1 | 0 |

`[PHP-only]` Add indentation to the output to make it more human-readable.


### Output details

| Parameter | Value | Default |
|-----------| ----- | ------- |
| addressdetails | 0 or 1 | 0 |

When set to 1, include a breakdown of the address into elements.

| Parameter | Value | Default |
|-----------| ----- | ------- |
| keywords  | 0 or 1 | 0 |

When set to 1, include a list of name keywords and address keywords
in the result.

| Parameter | Value | Default |
|-----------| ----- | ------- |
| linkedplaces  | 0 or 1 | 1 |

Include details of places that are linked with this one. Places get linked
together when they are different forms of the same physical object. Nominatim
links two kinds of objects together: place nodes get linked with the
corresponding administrative boundaries. Waterway relations get linked together with their
members.

| Parameter | Value | Default |
|-----------| ----- | ------- |
| hierarchy  | 0 or 1 | 0 |

Include details of places lower in the address hierarchy.

`[Python-only]` will only return properly parented places. These are address
or POI-like places that reuse the address of their parent street or place.

| Parameter | Value | Default |
|-----------| ----- | ------- |
| group_hierarchy  | 0 or 1 | 0 |

When set to 1, the output of the address hierarchy will be
grouped by type.

| Parameter | Value  | Default |
|-----------| -----  | ------- |
| polygon_geojson | 0 or 1 | 0 |


Include geometry of result.

### Language of results

| Parameter | Value | Default |
|-----------| ----- | ------- |
| accept-language | browser language string | content of "Accept-Language" HTTP header |

Preferred language order for showing search results. This may either be
a simple comma-separated list of language codes or have the same format
as the ["Accept-Language" HTTP header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language).


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

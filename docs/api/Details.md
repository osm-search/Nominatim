# Place details

Lookup details about a single place by id. The default output is HTML for debugging search logic and results.

**The details page (including JSON output) is there for debugging only and may not be downloaded automatically**, see [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).


## Parameters

The details API has the following two formats:

```
  https://nominatim.openstreetmap.org/details?osmtype=[N|W|R]&osmid=<value>
```

Both parameters are mandatory, the type is one of node(N), way(W) or relation(R). Up to 50 ids
can be queried at the same time.

Or

```
  https://nominatim.openstreetmap.org/details?placeid=<value>
```

The placeid created assigned sequentially during Nominatim data import. It is different between servers and changes when data gets reimported. Therefore it can't be used as permanent id and shouldn't be used in bug reports.


Additional optional parameters are explained below.

### Output format

* `format=[html|json]`

See [Place Output Formats](Output.md) for details on each format. (Default: html)

* `json_callback=<string>`

Wrap json output in a callback function (JSONP) i.e. `<string>(<json>)`.
Only has an effect for JSON output formats.

* `pretty=[0,1]`

Add indentation to JSON output to make it the output more human-readable. (Default: 0)


### Output details

* `addressdetails=[0|1]`

Include a breakdown of the address into elements. (Default for JSON: 0, for HTML: 1)

* `keywords=[0|1]`

Include a list of name keywords and address keywords (word ids). (Default: 0)

* `linkedplaces=[0|1]`

Include details of places which are higher in the address hierarchy. E.g. for a street this is usually the city, state, postal code, country. (Default: 1)

* `hierarchy=[0|1]`

Include details of places which are lower in the address hierarchy. E.g. for a city this usually a list of suburbs, rivers, streets. (Default for JSON: 0, for HTML: 1)

* `group_hierarchy=[0|1]`

For JSON output will group the places by type. (Default: 0)

* `polygon_geojson=[0|1]`

Include geometry of result. (Default for JSON: 0, for HTML: 1)

### Language of results

* `accept-language=<browser language string>`

Preferred language order for showing search results, overrides the value
specified in the "Accept-Language" HTTP header.
Either use a standard RFC2616 accept-language string or a simple
comma-separated list of language codes.


## Examples

##### HTML

[https://nominatim.openstreetmap.org/details.php?osmtype=W&osmid=38210407]()

##### JSON

[https://nominatim.openstreetmap.org/details.php?osmtype=W&osmid=38210407&format=json]()


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

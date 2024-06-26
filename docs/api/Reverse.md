# Reverse Geocoding

Reverse geocoding generates an address from a coordinate given as
latitude and longitude.

## How it works

The reverse geocoding API does not exactly compute the address for the
coordinate it receives. It works by finding the closest suitable OSM object
and returning its address information. This may occasionally lead to
unexpected results.

First of all, Nominatim only includes OSM objects in
its index that are suitable for searching. Small, unnamed paths for example
are missing from the database and can therefore not be used for reverse
geocoding either.

The other issue to be aware of is that the closest OSM object may not always
have a similar enough address to the coordinate you were requesting. For
example, in dense city areas it may belong to a completely different street.

## Endpoint

The main format of the reverse API is

```
https://nominatim.openstreetmap.org/reverse?lat=<value>&lon=<value>&<params>
```

where `lat` and `lon` are latitude and longitude of a coordinate in WGS84
projection. The API returns exactly one result or an error when the coordinate
is in an area with no OSM data coverage.


!!! danger "Deprecation warning"
    The reverse API used to allow address lookup for a single OSM object by
    its OSM id for `[PHP-only]`. The use is considered deprecated.
    Use the [Address Lookup API](Lookup.md) instead.

!!! danger "Deprecation warning"
    The API can also be used with the URL
    `https://nominatim.openstreetmap.org/reverse.php`. This is now deprecated
    and will be removed in future versions.


## Parameters

This section lists additional parameters to further influence the output.

### Output format

| Parameter | Value | Default |
|-----------| ----- | ------- |
| format    | one of: `xml`, `json`, `jsonv2`, `geojson`, `geocodejson` | `xml` |

See [Place Output Formats](Output.md) for details on each format.


| Parameter | Value | Default |
|-----------| ----- | ------- |
| json_callback | function name | _unset_ |

When given, then JSON output will be wrapped in a callback function with
the given name. See [JSONP](https://en.wikipedia.org/wiki/JSONP) for more
information.

Only has an effect for JSON output formats.


### Output details

| Parameter | Value | Default |
|-----------| ----- | ------- |
| addressdetails | 0 or 1 | 1 |

When set to 1, include a breakdown of the address into elements.
The exact content of the address breakdown depends on the output format.

!!! tip
    If you are interested in a stable classification of address categories
    (suburb, city, state, etc), have a look at the `geocodejson` format.
    All other formats return classifications according to OSM tagging.
    There is a much larger set of categories and they are not always consistent,
    which makes them very hard to work with.


| Parameter | Value | Default |
|-----------| ----- | ------- |
| extratags | 0 or 1 | 0 |

When set to 1, the response include any additional information in the result
that is available in the database, e.g. wikipedia link, opening hours.


| Parameter | Value | Default |
|-----------| ----- | ------- |
| namedetails | 0 or 1 | 0 |

When set to 1, include a full list of names for the result. These may include
language variants, older names, references and brand.


### Language of results

| Parameter | Value | Default |
|-----------| ----- | ------- |
| accept-language | browser language string | content of "Accept-Language" HTTP header |

Preferred language order for showing search results. This may either be
a simple comma-separated list of language codes or have the same format
as the ["Accept-Language" HTTP header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language).

!!! tip
    First-time users of Nominatim tend to be confused that they get different
    results when using Nominatim in the browser versus in a command-line tool
    like wget or curl. The command-line tools
    usually don't send any Accept-Language header, prompting Nominatim
    to show results in the local language. Browsers on the contrary always
    send the currently chosen browser language.


### Result restriction

| Parameter | Value | Default |
|-----------| ----- | ------- |
| zoom      | 0-18  | 18      |

Level of detail required for the address. This is a number that
corresponds roughly to the zoom level used in XYZ tile sources in frameworks
like Leaflet.js, Openlayers etc.
In terms of address details the zoom levels are as follows:

 zoom | address detail
 -----|---------------
  3   | country
  5   | state
  8   | county
  10  | city
  12  | town / borough
  13  | village / suburb
  14  | neighbourhood
  15  | any settlement
  16  | major streets
  17  | major and minor streets
  18  | building


| Parameter | Value | Default |
|-----------| ----- | ------- |
| layer     | comma-separated list of: `address`, `poi`, `railway`, `natural`, `manmade` | _unset_ (no restriction) |

**`[Python-only]`**

The layer filter allows to select places by themes.

The `address` layer contains all places that make up an address:
address points with house numbers, streets, inhabited places (suburbs, villages,
cities, states etc.) and administrative boundaries.

The `poi` layer selects all point of interest. This includes classic points
of interest like restaurants, shops, hotels but also less obvious features
like recycling bins, guideposts or benches.

The `railway` layer includes railway infrastructure like tracks.
Note that in Nominatim's standard configuration, only very few railway
features are imported into the database.

The `natural` layer collects features like rivers, lakes and mountains while
the `manmade` layer functions as a catch-all for features not covered by the
other layers.


### Polygon output

| Parameter | Value  | Default |
|-----------| -----  | ------- |
| polygon_geojson | 0 or 1 | 0 |
| polygon_kml     | 0 or 1 | 0 |
| polygon_svg     | 0 or 1 | 0 |
| polygon_text    | 0 or 1 | 0 |

Add the full geometry of the place to the result output. Output formats
in GeoJSON, KML, SVG or WKT are supported. Only one of these
options can be used at a time.

| Parameter | Value  | Default |
|-----------| -----  | ------- |
| polygon_threshold | floating-point number | 0.0 |

When one of the polygon_* outputs is chosen, return a simplified version
of the output geometry. The parameter describes the
tolerance in degrees with which the geometry may differ from the original
geometry. Topology is preserved in the geometry.


### Other

| Parameter | Value  | Default |
|-----------| -----  | ------- |
| email     | valid email address | _unset_ |

If you are making large numbers of request please include an appropriate email
address to identify your requests. See Nominatim's
[Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) for more details.


| Parameter | Value  | Default |
|-----------| -----  | ------- |
| debug     | 0 or 1 | 0       |

Output assorted developer debug information. Data on internals of Nominatim's
"search loop" logic, and SQL queries. The output is HTML format.
This overrides the specified machine readable format.


## Examples

* [https://nominatim.openstreetmap.org/reverse?format=xml&lat=52.5487429714954&lon=-1.81602098644987&zoom=18&addressdetails=1](https://nominatim.openstreetmap.org/reverse?format=xml&lat=52.5487429714954&lon=-1.81602098644987&zoom=18&addressdetails=1)

```xml
  <reversegeocode timestamp="Fri, 06 Nov 09 16:33:54 +0000" querystring="...">
    <result place_id="1620612" osm_type="node" osm_id="452010817">
      135, Pilkington Avenue, Wylde Green, City of Birmingham, West Midlands (county), B72, United Kingdom
    </result>
    <addressparts>
      <house_number>135</house_number>
      <road>Pilkington Avenue</road>
      <village>Wylde Green</village>
      <town>Sutton Coldfield</town>
      <city>City of Birmingham</city>
      <county>West Midlands (county)</county>
      <postcode>B72</postcode>
      <country>United Kingdom</country>
      <country_code>gb</country_code>
    </addressparts>
  </reversegeocode>
```

##### Example with `format=jsonv2`

* [https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=-34.44076&lon=-58.70521](https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=-34.44076&lon=-58.70521)

```json
{
  "place_id":"134140761",
  "licence":"Data © OpenStreetMap contributors, ODbL 1.0. https:\/\/www.openstreetmap.org\/copyright",
  "osm_type":"way",
  "osm_id":"280940520",
  "lat":"-34.4391708",
  "lon":"-58.7064573",
  "place_rank":"26",
  "category":"highway",
  "type":"motorway",
  "importance":"0.1",
  "addresstype":"road",
  "display_name":"Autopista Pedro Eugenio Aramburu, El Triángulo, Partido de Malvinas Argentinas, Buenos Aires, 1.619, Argentina",
  "name":"Autopista Pedro Eugenio Aramburu",
  "address":{
    "road":"Autopista Pedro Eugenio Aramburu",
    "village":"El Triángulo",
    "state_district":"Partido de Malvinas Argentinas",
    "state":"Buenos Aires",
    "postcode":"1.619",
    "country":"Argentina",
    "country_code":"ar"
  },
  "boundingbox":["-34.44159","-34.4370994","-58.7086067","-58.7044712"]
}
```

##### Example with `format=geojson`

* [https://nominatim.openstreetmap.org/reverse?format=geojson&lat=44.50155&lon=11.33989](https://nominatim.openstreetmap.org/reverse?format=geojson&lat=44.50155&lon=11.33989)

```json
{
  "type": "FeatureCollection",
  "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "place_id": "18512203",
        "osm_type": "node",
        "osm_id": "1704756187",
        "place_rank": "30",
        "category": "place",
        "type": "house",
        "importance": "0",
        "addresstype": "place",
        "name": null,
        "display_name": "71, Via Guglielmo Marconi, Saragozza-Porto, Bologna, BO, Emilia-Romagna, 40122, Italy",
        "address": {
          "house_number": "71",
          "road": "Via Guglielmo Marconi",
          "suburb": "Saragozza-Porto",
          "city": "Bologna",
          "county": "BO",
          "state": "Emilia-Romagna",
          "postcode": "40122",
          "country": "Italy",
          "country_code": "it"
        }
      },
      "bbox": [
        11.3397676,
        44.5014307,
        11.3399676,
        44.5016307
      ],
      "geometry": {
        "type": "Point",
        "coordinates": [
          11.3398676,
          44.5015307
        ]
      }
    }
  ]
}
```

##### Example with `format=geocodejson`

[https://nominatim.openstreetmap.org/reverse?format=geocodejson&lat=60.2299&lon=11.1663](https://nominatim.openstreetmap.org/reverse?format=geocodejson&lat=60.2299&lon=11.1663)

```json
{
  "type": "FeatureCollection",
  "geocoding": {
    "version": "0.1.0",
    "attribution": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
    "licence": "ODbL",
    "query": "60.229917843587,11.16630979382"
  },
  "features": {
    "type": "Feature",
    "properties": {
      "geocoding": {
        "place_id": "42700574",
        "osm_type": "node",
        "osm_id": "3110596255",
        "type": "house",
        "accuracy": 0,
        "label": "1, Løvenbergvegen, Mogreina, Ullensaker, Akershus, 2054, Norway",
        "name": null,
        "housenumber": "1",
        "street": "Løvenbergvegen",
        "postcode": "2054",
        "county": "Akershus",
        "country": "Norway",
        "admin": {
          "level7": "Ullensaker",
          "level4": "Akershus",
          "level2": "Norway"
        }
      }
    },
    "geometry": {
      "type": "Point",
      "coordinates": [
        11.1658572,
        60.2301296
      ]
    }
  }
}
```


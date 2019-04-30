# Reverse Geocoding

Reverse geocoding generates an address from a latitude and longitude or from
an OSM object.

## Parameters

The main format of the reverse API is

```
https://nominatim.openstreetmap.org/reverse?<query>
```

There are two ways how the requested location can be specified:

* `lat=<value>` `lon=<value>`

    A geographic location to generate an address for. The coordiantes must be
    in WGS84 format.

* `osm_type=[N|W|R]` `osm_id=<value>`

    A specific OSM node(N), way(W) or relation(R) to return an address for.

In both cases exactly one object is returned. The two input paramters cannot
be used at the same time. Both accept the additional optional parameters listed
below.

### Output format

* `format=[xml|json|jsonv2|geojson|geocodejson]`

See [Place Output Formats](Output.md) for details on each format. (Default: html)

* `json_callback=<string>`

Wrap json output in a callback function ([JSONP](https://en.wikipedia.org/wiki/JSONP)) i.e. `<string>(<json>)`.
Only has an effect for JSON output formats.

### Output details

* `addressdetails=[0|1]`

Include a breakdown of the address into elements. (Default: 1)


* `extratags=[0|1]`

Include additional information in the result if available,
e.g. wikipedia link, opening hours. (Default: 0)


* `namedetails=[0|1]`

Include a list of alternative names in the results. These may include
language variants, references, operator and brand. (Default: 0)


### Language of results

* `accept-language=<browser language string>`

Preferred language order for showing search results, overrides the value
specified in the "Accept-Language" HTTP header.
Either use a standard RFC2616 accept-language string or a simple
comma-separated list of language codes.

### Result limitation

* `zoom=[0-18]`

Level of detail required for the address. Default: 18. This is a number that corresponds
roughly to the zoom level used in map frameworks like Leaflet.js, Openlayers etc.
In terms of address details the zoom levels are as follows:

 zoom | address detail
 -----|---------------
  3   | country
  5   | state
  8   | county
  10  | city
  14  | suburb
  16  | major streets
  17  | major and minor streets
  18  | building


### Polygon output

* `polygon_geojson=1`
* `polygon_kml=1`
* `polygon_svg=1`
* `polygon_text=1`

Output geometry of results as a GeoJSON, KML, SVG or WKT. Only one of these
options can be used at a time. (Default: 0)

* `polygon_threshold=0.0`

Simplify the output geometry before returning. The parameter is the
tolerance in degrees with which the geometry may differ from the original
geometry. Topology is preserved in the result. (Default: 0.0)

### Other

* `email=<valid email address>`

If you are making large numbers of request please include an appropriate email
address to identify your requests. See Nominatim's [Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) for more details.


* `debug=[0|1]`

Output assorted developer debug information. Data on internals of Nominatim's
"Search Loop" logic, and SQL queries. The output is (rough) HTML format.
This overrides the specified machine readable format. (Default: 0)


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
  "licence":"Data © OpenStreetMap contributors, ODbL 1.0. http:\/\/www.openstreetmap.org\/copyright",
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


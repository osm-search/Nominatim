# Search queries

The search API allows to look up a location from a textual description.
Nominatim supports structured as well as free-form search queries.

The search query may also contain
[special phrases](https://wiki.openstreetmap.org/wiki/Nominatim/Special_Phrases)
which are tranlated into specific OpenStreetMap(OSM) tags (e.g. Pub => amenity=pub).
Note that this only limits the items to be found. It is not suited to return complete
lists of OSM objects of a specific type.
Use [Overpass API](https://overpass-api.de/) for that.

## Parameters

The search API has the following two formats:

```
   https://nominatim.openstreetmap.org/search/<query>?<params>
```

This format only accepts a free-form query string where the
parts of the query are separated by slashes.

```
   https://nominatim.openstreetmap.org/search?<params>
```

In this form, the query may be given through two different sets of parameters:

* `q=<query>`

    Free-form query string to search for.
    Free-form queries are processed first left to right and then right to
    left if that fails. So you may search for
    [pilkington avenue, birmingham](//nominatim.openstreetmap.org/search?q=pilkington+avenue,birmingham) as well as for
    [birmingham, pilkington avenue](//nominatim.openstreetmap.org/search?q=birmingham,+pilkington+avenue).
    Commas are optional, but improve performance by reducing the complexity
    of the search.


* `street=<housenumber> <streetname>`
  `city=<city>`
  `county=<county>`
  `state=<state>`
  `country=<country>`
  `postalcode=<postalcode>`

    Alternative query string format for structured requests.
    Structured requests are faster but are less robust against alternative
    OSM tagging schemas. **Do not combine with** `q=<query>` **parameter**.

All three query forms accept the additional paramters listed below.

### Output format

* `format=[html|xml|json|jsonv2|geojson|geocodejson]`

See [Place Output Formats](Output.md) for details on each format. (Default: html)

* `json_callback=<string>`

Wrap json output in a callback function (JSONP) i.e. `<string>(<json>)`.
Only has an effect for JSON output formats.

### Output details

* `addressdetails=[0|1]`

Include a breakdown of the address into elements. (Default: 0)


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

* `countrycodes=<countrycode>[,<countrycode>][,<countrycode>]...`

Limit search results to one or more countries. `<countrycode>` must be the
ISO 3166-1alpha2 code, e.g. `gb` for the United Kingdom, `de` for Germany.


* `exclude_place_ids=<place_id,[place_id],[place_id]`

If you do not want certain OSM objects to appear in the search
result, give a comma separated list of the `place_id`s you want to skip.
This can be used to broaden search results. For example, if a previous
query only returned a few results, then including those here would cause
the search to return other, less accurate, matches (if possible).


* `limit=<integer>`

Limit the number of returned results. (Default: 10)


* `viewbox=<x1>,<y1>,<x2>,<y2>`

The preferred area to find search results. Any two corner points of the box
are accepted in any order as long as they span a real box.


* `bounded=[0|1]`

When a viewbox is given, restrict the result to items contained with that
viewbox (see above). When `viewbox` and `bounded` are given, an amenity
only search is allowed. In this case, give the special keyword for the
amenity in squaer brackets, e.g. `[pub]`. (Default: 0)


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

* `dedupe=[0|1]`

Sometimes you have several objects in OSM identifying the same place or
object in reality. The simplest case is a street being split in many
different OSM ways due to different characteristics. Nominatim will
attempt to detect such duplicates and only return one match unless
this parameter is set to 0. (Default: 1)



* `debug=[0|1]`

Output assorted developer debug information. Data on internals of Nominatim's
"Search Loop" logic, and SQL queries. The output is (rough) HTML format.
This overrides the specified machine readable format. (Default: 0)



## Examples


##### XML with polygon points

* [https://nominatim.openstreetmap.org/search?q=135+pilkington+avenue,+birmingham&format=xml&polygon=1&addressdetails=1](https://nominatim.openstreetmap.org/search?q=135+pilkington+avenue,+birmingham&format=xml&polygon=1&addressdetails=1)
* [https://nominatim.openstreetmap.org/search/gb/birmingham/pilkington%20avenue/135?format=xml&polygon=1&addressdetails=1](https://nominatim.openstreetmap.org/search/gb/birmingham/pilkington%20avenue/135?format=xml&polygon=1&addressdetails=1)
* [https://nominatim.openstreetmap.org/search/135%20pilkington%20avenue,%20birmingham?format=xml&polygon=1&addressdetails=1](https://nominatim.openstreetmap.org/search/135%20pilkington%20avenue,%20birmingham?format=xml&polygon=1&addressdetails=1)

```xml
  <searchresults timestamp="Sat, 07 Nov 09 14:42:10 +0000" querystring="135 pilkington, avenue birmingham" polygon="true">
    <place 
      place_id="1620612" osm_type="node" osm_id="452010817" 
      boundingbox="52.548641204834,52.5488433837891,-1.81612110137939,-1.81592094898224" 
      polygonpoints="[['-1.81592098644987','52.5487429714954'],['-1.81592290792183','52.5487234624632'],...]" 
      lat="52.5487429714954" lon="-1.81602098644987" 
      display_name="135, Pilkington Avenue, Wylde Green, City of Birmingham, West Midlands (county), B72, United Kingdom" 
      class="place" type="house">
      <house_number>135</house_number>
      <road>Pilkington Avenue</road>
      <village>Wylde Green</village>
      <town>Sutton Coldfield</town>
      <city>City of Birmingham</city>
      <county>West Midlands (county)</county>
      <postcode>B72</postcode>
      <country>United Kingdom</country>
      <country_code>gb</country_code>
    </place>
  </searchresults>
```

##### JSON with SVG polygon

[https://nominatim.openstreetmap.org/search/Unter%20den%20Linden%201%20Berlin?format=json&addressdetails=1&limit=1&polygon_svg=1](https://nominatim.openstreetmap.org/search/Unter%20den%20Linden%201%20Berlin?format=json&addressdetails=1&limit=1&polygon_svg=1)

```json
    {
        "address": {
            "city": "Berlin",
            "city_district": "Mitte",
            "construction": "Unter den Linden",
            "continent": "European Union",
            "country": "Deutschland",
            "country_code": "de",
            "house_number": "1",
            "neighbourhood": "Scheunenviertel",
            "postcode": "10117",
            "public_building": "Kommandantenhaus",
            "state": "Berlin",
            "suburb": "Mitte"
        },
        "boundingbox": [
            "52.5170783996582",
            "52.5173187255859",
            "13.3975105285645",
            "13.3981599807739"
        ],
        "class": "amenity",
        "display_name": "Kommandantenhaus, 1, Unter den Linden, Scheunenviertel, Mitte, Berlin, 10117, Deutschland, European Union",
        "importance": 0.73606775332943,
        "lat": "52.51719785",
        "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright",
        "lon": "13.3978352028938",
        "osm_id": "15976890",
        "osm_type": "way",
        "place_id": "30848715",
        "svg": "M 13.397511 -52.517283599999999 L 13.397829400000001 -52.517299800000004 13.398131599999999 -52.517315099999998 13.398159400000001 -52.517112099999999 13.3975388 -52.517080700000001 Z",
        "type": "public_building"
    }
```

##### JSON with address details

[https://nominatim.openstreetmap.org/?format=json&addressdetails=1&q=bakery+in+berlin+wedding&format=json&limit=1](https://nominatim.openstreetmap.org/?format=json&addressdetails=1&q=bakery+in+berlin+wedding&format=json&limit=1)

```json
    {
        "address": {
            "bakery": "B\u00e4cker Kamps",
            "city_district": "Mitte",
            "continent": "European Union",
            "country": "Deutschland",
            "country_code": "de",
            "footway": "Bahnsteig U6",
            "neighbourhood": "Sprengelkiez",
            "postcode": "13353",
            "state": "Berlin",
            "suburb": "Wedding"
        },
        "boundingbox": [
            "52.5460929870605",
            "52.5460968017578",
            "13.3591794967651",
            "13.3591804504395"
        ],
        "class": "shop",
        "display_name": "B\u00e4cker Kamps, Bahnsteig U6, Sprengelkiez, Wedding, Mitte, Berlin, 13353, Deutschland, European Union",
        "icon": "https://nominatim.openstreetmap.org/images/mapicons/shopping_bakery.p.20.png",
        "importance": 0.201,
        "lat": "52.5460941",
        "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright",
        "lon": "13.35918",
        "osm_id": "317179427",
        "osm_type": "node",
        "place_id": "1453068",
        "type": "bakery"
    }
```

##### GeoJSON

[https://nominatim.openstreetmap.org/search?q=17+Strada+Pictor+Alexandru+Romano%2C+Bukarest&format=geojson](https://nominatim.openstreetmap.org/search?q=17+Strada+Pictor+Alexandru+Romano%2C+Bukarest&format=geojson)

```json
{
  "type": "FeatureCollection",
  "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "place_id": "35811445",
        "osm_type": "node",
        "osm_id": "2846295644",
        "display_name": "17, Strada Pictor Alexandru Romano, Bukarest, Bucharest, Sector 2, Bucharest, 023964, Romania",
        "place_rank": "30",
        "category": "place",
        "type": "house",
        "importance": 0.62025
      },
      "bbox": [
        26.1156689,
        44.4354754,
        26.1157689,
        44.4355754
      ],
      "geometry": {
        "type": "Point",
        "coordinates": [
          26.1157189,
          44.4355254
        ]
      }
    }
  ]
}
```

##### GeocodeJSON

[https://nominatim.openstreetmap.org/search?q=%CE%91%CE%B3%CE%AF%CE%B1+%CE%A4%CF%81%CE%B9%CE%AC%CE%B4%CE%B1%2C+%CE%91%CE%B4%CF%89%CE%BD%CE%B9%CE%B4%CE%BF%CF%82%2C+Athens%2C+Greece&format=geocodejson](https://nominatim.openstreetmap.org/search?q=%CE%91%CE%B3%CE%AF%CE%B1+%CE%A4%CF%81%CE%B9%CE%AC%CE%B4%CE%B1%2C+%CE%91%CE%B4%CF%89%CE%BD%CE%B9%CE%B4%CE%BF%CF%82%2C+Athens%2C+Greece&format=geocodejson)

```json
{
  "type": "FeatureCollection",
  "geocoding": {
    "version": "0.1.0",
    "attribution": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
    "licence": "ODbL",
    "query": "Αγία Τριάδα, Αδωνιδος, Athens, Greece"
  },
  "features": [
    {
      "type": "Feature",
      "properties": {
        "geocoding": {
          "type": "place_of_worship",
          "label": "Αγία Τριάδα, Αδωνιδος, Άγιος Νικόλαος, 5º Δημοτικό Διαμέρισμα Αθηνών, Athens, Municipality of Athens, Regional Unit of Central Athens, Region of Attica, Attica, 11472, Greece",
          "name": "Αγία Τριάδα",
          "admin": null
        }
      },
      "geometry": {
        "type": "Point",
        "coordinates": [
          23.72949633941,
          38.0051697
        ]
      }
    }
  ]
}
```

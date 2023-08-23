# Search queries

The search API allows you to look up a location from a textual description
or address. Nominatim supports structured and free-form search queries.

The search query may also contain
[special phrases](https://wiki.openstreetmap.org/wiki/Nominatim/Special_Phrases)
which are translated into specific OpenStreetMap (OSM) tags (e.g. Pub => `amenity=pub`).
This can be used to narrow down the kind of objects to be returned.

!!! warning
    Special phrases are not suitable to query all objects of a certain type in an
    area. Nominatim will always just return a collection of the best matches. To
    download OSM data by object type, use the [Overpass API](https://overpass-api.de/).

## Parameters

The search API has the following format:

```
   https://nominatim.openstreetmap.org/search?<params>
```

The search term may be specified with two different sets of parameters:

* `q=<query>`

    Free-form query string to search for.
    Free-form queries are processed first left-to-right and then right-to-left if that fails. So you may search for
    [pilkington avenue, birmingham](https://nominatim.openstreetmap.org/search?q=pilkington+avenue,birmingham) as well as for
    [birmingham, pilkington avenue](https://nominatim.openstreetmap.org/search?q=birmingham,+pilkington+avenue).
    Commas are optional, but improve performance by reducing the complexity of the search.

* `amenity=<name and/or type of POI>`
* `street=<housenumber> <streetname>`
* `city=<city>`
* `county=<county>`
* `state=<state>`
* `country=<country>`
* `postalcode=<postalcode>`

    Alternative query string format split into several parameters for structured requests.
    Structured requests are faster but are less robust against alternative
    OSM tagging schemas. **Do not combine with** `q=<query>` **parameter**.

Both query forms accept the additional parameters listed below.

### Output format

* `format=[xml|json|jsonv2|geojson|geocodejson]`

See [Place Output Formats](Output.md) for details on each format. (Default: jsonv2)

!!! note
    The Nominatim service at
    [https://nominatim.openstreetmap.org](https://nominatim.openstreetmap.org)
    has a different default behaviour for historical reasons. When the
    `format` parameter is omitted, the request will be forwarded to the Web UI.

* `json_callback=<string>`

Wrap JSON output in a callback function ([JSONP](https://en.wikipedia.org/wiki/JSONP)) i.e. `<string>(<json>)`.
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
specified in the ["Accept-Language" HTTP header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language).
Either use a standard RFC2616 accept-language string or a simple
comma-separated list of language codes.

### Result limitation

* `countrycodes=<countrycode>[,<countrycode>][,<countrycode>]...`

Limit search results to one or more countries. `<countrycode>` must be the
[ISO 3166-1alpha2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code,
e.g. `gb` for the United Kingdom, `de` for Germany.

Each place in Nominatim is assigned to one country code based
on OSM country boundaries. In rare cases a place may not be in any country
at all, for example, in international waters.

* `exclude_place_ids=<place_id,[place_id],[place_id]`

If you do not want certain OSM objects to appear in the search
result, give a comma separated list of the `place_id`s you want to skip.
This can be used to retrieve additional search results. For example, if a
previous query only returned a few results, then including those here would
cause the search to return other, less accurate, matches (if possible).


* `limit=<integer>`

Limit the number of returned results. (Default: 10, Maximum: 50)


* `viewbox=<x1>,<y1>,<x2>,<y2>`

The preferred area to find search results. Any two corner points of the box
are accepted as long as they span a real box. `x` is longitude,
`y` is latitude.


* `bounded=[0|1]`

When a viewbox is given, restrict the result to items contained within that
viewbox (see above). When `viewbox` and `bounded=1` are given, an amenity
only search is allowed. Give the special keyword for the amenity in square
brackets, e.g. `[pub]` and a selection of objects of this type is returned.
There is no guarantee that the result is complete. (Default: 0)


### Polygon output

* `polygon_geojson=1`
* `polygon_kml=1`
* `polygon_svg=1`
* `polygon_text=1`

Output geometry of results as a GeoJSON, KML, SVG or WKT. Only one of these
options can be used at a time. (Default: 0)

* `polygon_threshold=0.0`

Return a simplified version of the output geometry. The parameter is the
tolerance in degrees with which the geometry may differ from the original
geometry. Topology is preserved in the result. (Default: 0.0)

### Other

* `email=<valid email address>`

If you are making large numbers of request please include an appropriate email
address to identify your requests. See Nominatim's [Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) for more details.

* `dedupe=[0|1]`

Sometimes you have several objects in OSM identifying the same place or
object in reality. The simplest case is a street being split into many
different OSM ways due to different characteristics. Nominatim will
attempt to detect such duplicates and only return one match unless
this parameter is set to 0. (Default: 1)

* `debug=[0|1]`

Output assorted developer debug information. Data on internals of Nominatim's
"Search Loop" logic, and SQL queries. The output is (rough) HTML format.
This overrides the specified machine readable format. (Default: 0)



## Examples


##### XML with KML polygon

* [https://nominatim.openstreetmap.org/search?q=135+pilkington+avenue,+birmingham&format=xml&polygon_kml=1&addressdetails=1](https://nominatim.openstreetmap.org/search?q=135+pilkington+avenue,+birmingham&format=xml&polygon_kml=1&addressdetails=1)

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<searchresults timestamp="Tue, 08 Aug 2023 15:45:41 +00:00"
               attribution="Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright"
               querystring="135 pilkington avenue, birmingham"
               more_url="https://nominatim.openstreetmap.org/search?q=135+pilkington+avenue%2C+birmingham&amp;polygon_kml=1&amp;addressdetails=1&amp;limit=20&amp;exclude_place_ids=125279639&amp;format=xml"
               exclude_place_ids="125279639">
  <place place_id="125279639"
         osm_type="way"
         osm_id="90394480"
         lat="52.5487921"
         lon="-1.8164308"
         boundingbox="52.5487473,52.5488481,-1.8165130,-1.8163464"
         place_rank="30"
         address_rank="30"
         display_name="135, Pilkington Avenue, Maney, Sutton Coldfield, Wylde Green, Birmingham, West Midlands Combined Authority, England, B72 1LH, United Kingdom"
         class="building"
         type="residential"
         importance="9.999999994736442e-08">
    <geokml>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>-1.816513,52.5487566 -1.816434,52.5487473 -1.816429,52.5487629 -1.8163717,52.5487561 -1.8163464,52.5488346 -1.8164599,52.5488481 -1.8164685,52.5488213 -1.8164913,52.548824 -1.816513,52.5487566</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </geokml>
    <house_number>135</house_number>
    <road>Pilkington Avenue</road>
    <hamlet>Maney</hamlet>
    <town>Sutton Coldfield</town>
    <village>Wylde Green</village>
    <city>Birmingham</city>
    <ISO3166-2-lvl8>GB-BIR</ISO3166-2-lvl8>
    <state_district>West Midlands Combined Authority</state_district>
    <state>England</state>
    <ISO3166-2-lvl4>GB-ENG</ISO3166-2-lvl4>
    <postcode>B72 1LH</postcode>
    <country>United Kingdom</country>
    <country_code>gb</country_code>
  </place>
</searchresults>
```

##### JSON with SVG polygon

[https://nominatim.openstreetmap.org/search?q=Unter%20den%20Linden%201%20Berlin&format=json&addressdetails=1&limit=1&polygon_svg=1](https://nominatim.openstreetmap.org/search?q=Unter%20den%20Linden%201%20Berlin&format=json&addressdetails=1&limit=1&polygon_svg=1)

```json
[
  {
    "address": {
      "ISO3166-2-lvl4": "DE-BE",
      "borough": "Mitte",
      "city": "Berlin",
      "country": "Deutschland",
      "country_code": "de",
      "historic": "Kommandantenhaus",
      "house_number": "1",
      "neighbourhood": "Friedrichswerder",
      "postcode": "10117",
      "road": "Unter den Linden",
      "suburb": "Mitte"
    },
    "boundingbox": [
      "52.5170798",
      "52.5173311",
      "13.3975116",
      "13.3981577"
    ],
    "class": "historic",
    "display_name": "Kommandantenhaus, 1, Unter den Linden, Friedrichswerder, Mitte, Berlin, 10117, Deutschland",
    "importance": 0.8135042058306902,
    "lat": "52.51720765",
    "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
    "lon": "13.397834399325466",
    "osm_id": 15976890,
    "osm_type": "way",
    "place_id": 108681845,
    "svg": "M 13.3975116 -52.5172905 L 13.397549 -52.5170798 13.397715 -52.5170906 13.3977122 -52.5171064 13.3977392 -52.5171086 13.3977417 -52.5170924 13.3979655 -52.5171069 13.3979623 -52.5171233 13.3979893 -52.5171248 13.3979922 -52.5171093 13.3981577 -52.5171203 13.398121 -52.5173311 13.3978115 -52.5173103 Z",
    "type": "house"
  }
]
```

##### JSON with address details

[https://nominatim.openstreetmap.org/search?addressdetails=1&q=bakery+in+berlin+wedding&format=jsonv2&limit=1](https://nominatim.openstreetmap.org/search?addressdetails=1&q=bakery+in+berlin+wedding&format=jsonv2&limit=1)

```json
[
  {
    "address": {
      "ISO3166-2-lvl4": "DE-BE",
      "borough": "Mitte",
      "city": "Berlin",
      "country": "Deutschland",
      "country_code": "de",
      "neighbourhood": "Sprengelkiez",
      "postcode": "13347",
      "road": "Lindower Straße",
      "shop": "Ditsch",
      "suburb": "Wedding"
    },
    "addresstype": "shop",
    "boundingbox": [
      "52.5427201",
      "52.5427654",
      "13.3668619",
      "13.3669442"
    ],
    "category": "shop",
    "display_name": "Ditsch, Lindower Straße, Sprengelkiez, Wedding, Mitte, Berlin, 13347, Deutschland",
    "importance": 9.99999999995449e-06,
    "lat": "52.54274275",
    "licence": "Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright",
    "lon": "13.36690305710228",
    "name": "Ditsch",
    "osm_id": 437595031,
    "osm_type": "way",
    "place_id": 204751033,
    "place_rank": 30,
    "type": "bakery"
  }
]
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

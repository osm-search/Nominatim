
## Search
Nominatim indexes named (or numbered) features with the OSM data set and a subset of other unnamed features (pubs, hotels, churches, etc)

Search terms are processed first left to right and then right to left if that fails.

Both searches will work: [pilkington avenue, birmingham](//nominatim.openstreetmap.org/search?q=pilkington+avenue,birmingham), [birmingham, pilkington avenue](//nominatim.openstreetmap.org/search?q=birmingham,+pilkington+avenue)

(Commas are optional, but improve performance by reducing the complexity of the search.)

Where house numbers have been defined for an area they should be used: [135 pilkington avenue, birmingham](//nominatim.openstreetmap.org/search?q=135+pilkington+avenue,+birmingham)

### Special Keywords
Various keywords are translated into searches for specific osm tags (e.g. Pub => amenity=pub).  A current list of [special phrases](https://wiki.openstreetmap.org/wiki/Nominatim/Special_Phrases) processed is available.

### Parameters

```
   https://nominatim.openstreetmap.org/search?<params>
   https://nominatim.openstreetmap.org/search/<query>?<params>
```

* `format=[html|xml|json|jsonv2]`

    * Output format
    * defaults to `html`


* `json_callback=<string>`

    * Wrap json output in a callback function (JSONP) i.e. `<string>(<json>)` 

* `accept-language=<browser language string>`

    * Preferred language order for showing search results, overrides the value specified in the "Accept-Language" HTTP header.
    * Either uses standard rfc2616 accept-language string or a simple comma separated list of language codes.

* `q=<query>`

    * Query string to search for.
    * Alternatively can be entered as:

        * `street=<housenumber> <streetname>`
        * `city=<city>`
        * `county=<county>`
        * `state=<state>`
        * `country=<country>`
        * `postalcode=<postalcode>`
        
      **(experimental)** Alternative query string format for structured requests. 
Structured requests are faster and require fewer server resources. **Do not combine with `q=<query>` parameter**.

* `countrycodes=<countrycode>[,<countrycode>][,<countrycode>]...`

    * Limit search results to a specific country (or a list of countries).  
    * `<countrycode>` should be the ISO 3166-1alpha2 code, e.g. `gb` for the United Kingdom, `de` for Germany, etc.

* `viewbox=<x1>,<y1>,<x2>,<y2>`
    * The preferred area to find search results. Any two corner points of the box are accepted in any order as long as they span a real box.

* `bounded=[0|1]`
    * defaults to 0
    * Restrict the results to only items contained with the viewbox (see above). 
    * Restricting the results to the bounding box also enables searching by amenity only. 
    * For example a search query of just `"[pub]"` would normally be rejected but with `bounded=1` will result in a list of items matching within the bounding box.

* `polygon=[0|1]`
    * defaults to 0
    * Output polygon outlines for items found **(deprecated, use one of the polygon_* parameters instead)**

* `addressdetails=[0|1]`
    * defaults to 0
    * Include a breakdown of the address into elements

* `email=<valid email address>`

    * If you are making large numbers of request please include a valid email address or alternatively include your email address as part of the User-Agent string.
    * This information will be kept confidential and only used to contact you in the event of a problem, see [Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) for more details.

* `exclude_place_ids=<place_id,[place_id],[place_id]`

    * If you do not want certain openstreetmap objects to appear in the search result, give a comma separated list of the place_id's you want to skip. This can be used to broaden search results. For example, if a previous query only returned a few results, then including those here would cause the search to return other, less accurate, matches (if possible)

* `limit=<integer>`
    * defaults to 10
    * Limit the number of returned results.

* `dedupe=[0|1]`
    * defaults to 1
    * Sometimes you have several objects in OSM identifying the same place or object in reality. The simplest case is a street being split in many different OSM ways due to different characteristics. 
    * Nominatim will attempt to detect such duplicates and only return one match; this is controlled by the dedupe parameter which defaults to 1. Since the limit is, for reasons of efficiency, enforced before and not after de-duplicating, it is possible that de-duplicating leaves you with less results than requested.

* `debug=[0|1]`
    * defaults to 0
    * Output assorted developer debug information. Data on internals of nominatim "Search Loop" logic, and SQL queries. The output is (rough) HTML format. This overrides the specified machine readable format.

* `polygon_geojson=1`
    * Output geometry of results in geojson format.

* `polygon_kml=1`
    * Output geometry of results in kml format.

* `polygon_svg=1`
    * Output geometry of results in svg format.

* `polygon_text=1`
    * Output geometry of results as a WKT.

* `polygon_threshold=0.0`
    * defaults to 0.0
    * Simplify the output geometry before returning. The parameter is the
      tolerance in degrees with which the geometry may differ from the original
      geometry. Topology is preserved in the result.

* `extratags=1`
    * Include additional information in the result if available, e.g. wikipedia link, opening hours.

* `namedetails=1`
    * Include a list of alternative names in the results.
    * These may include language variants, references, operator and brand.

### Examples

* [https://nominatim.openstreetmap.org/search?q=135+pilkington+avenue,+birmingham&format=xml&polygon=1&addressdetails=1](https://nominatim.openstreetmap.org/search?q=135+pilkington+avenue,+birmingham&format=xml&polygon=1&addressdetails=1)
* [https://nominatim.openstreetmap.org/search/135%20pilkington%20avenue,%20birmingham?format=xml&polygon=1&addressdetails=1](https://nominatim.openstreetmap.org/search/135%20pilkington%20avenue,%20birmingham?format=xml&polygon=1&addressdetails=1)
* [https://nominatim.openstreetmap.org/search/gb/birmingham/pilkington%20avenue/135?format=xml&polygon=1&addressdetails=1](https://nominatim.openstreetmap.org/search/gb/birmingham/pilkington%20avenue/135?format=xml&polygon=1&addressdetails=1)

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

* [https://nominatim.openstreetmap.org/search/Unter%20den%20Linden%201%20Berlin?format=json&addressdetails=1&limit=1&polygon_svg=1](https://nominatim.openstreetmap.org/search/Unter%20den%20Linden%201%20Berlin?format=json&addressdetails=1&limit=1&polygon_svg=1)

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

* [https://nominatim.openstreetmap.org/?format=json&addressdetails=1&q=bakery+in+berlin+wedding&format=json&limit=1](https://nominatim.openstreetmap.org/?format=json&addressdetails=1&q=bakery+in+berlin+wedding&format=json&limit=1)

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

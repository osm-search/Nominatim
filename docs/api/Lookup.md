# Address lookup

The lookup API allows to query the address and other details of one or
multiple OSM objects like node, way or relation.

## Parameters

The lookup API has the following format:

```
  https://nominatim.openstreetmap.org/lookup?osm_ids=[N|W|R]<value>,…,…,&<params>
```

`osm_ids` is mandatory and must contain a comma-separated list of OSM ids each
prefixed with its type, one of node(N), way(W) or relation(R). Up to 50 ids
can be queried at the same time.

Additional optional parameters are explained below.

### Output format

* `format=[xml|json|jsonv2|geojson|geocodejson]`

See [Place Output Formats](Output.md) for details on each format. (Default: xml)

* `json_callback=<string>`

Wrap JSON output in a callback function (JSONP) i.e. `<string>(<json>)`.
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

* `debug=[0|1]`

Output assorted developer debug information. Data on internals of Nominatim's
"Search Loop" logic, and SQL queries. The output is (rough) HTML format.
This overrides the specified machine readable format. (Default: 0)


## Examples

##### XML

[https://nominatim.openstreetmap.org/lookup?osm_ids=R146656,W104393803,N240109189](https://nominatim.openstreetmap.org/lookup?osm_ids=R146656,W50637691,N240109189)

```xml
  <lookupresults timestamp="Mon, 28 Mar 22 14:38:54 +0000" attribution="Data &#xA9; OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright" querystring="R146656,W50637691,N240109189" more_url="">
    <place place_id="282236157" osm_type="relation" osm_id="146656" place_rank="16" address_rank="16" boundingbox="53.3401044,53.5445923,-2.3199185,-2.1468288" lat="53.44246175" lon="-2.2324547359718547" display_name="Manchester, Greater Manchester, North West England, England, United Kingdom" class="boundary" type="administrative" importance="0.35">
      <city>Manchester</city>
      <county>Greater Manchester</county>
      <state_district>North West England</state_district>
      <state>England</state>
      <country>United Kingdom</country>
      <country_code>gb</country_code>
    </place>
    <place place_id="115462561" osm_type="way" osm_id="50637691" place_rank="30" address_rank="30" boundingbox="52.3994612,52.3996426,13.0479574,13.0481754" lat="52.399550700000006" lon="13.048066846939687" display_name="Brandenburger Tor, Brandenburger Stra&#xDF;e, Historische Innenstadt, Innenstadt, Potsdam, Brandenburg, 14467, Germany" class="tourism" type="attraction" importance="0.29402874005524">
      <tourism>Brandenburger Tor</tourism>
      <road>Brandenburger Stra&#xDF;e</road>
      <suburb>Historische Innenstadt</suburb>
      <city>Potsdam</city>
      <state>Brandenburg</state>
      <postcode>14467</postcode>
      <country>Germany</country>
      <country_code>de</country_code>
    </place>
    <place place_id="567505" osm_type="node" osm_id="240109189" place_rank="15" address_rank="16" boundingbox="52.3586925,52.6786925,13.2396024,13.5596024" lat="52.5186925" lon="13.3996024" display_name="Berlin, 10178, Germany" class="place" type="city" importance="0.78753902824914">
      <city>Berlin</city>
      <state>Berlin</state>
      <postcode>10178</postcode>
      <country>Germany</country>
      <country_code>de</country_code>
    </place>
  </lookupresults>
```

##### JSON with extratags

[https://nominatim.openstreetmap.org/lookup?osm_ids=W50637691&format=json&extratags=1](https://nominatim.openstreetmap.org/lookup?osm_ids=W50637691&format=json&extratags=1)

```json
[
   {
      "place_id": 115462561,
      "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
      "osm_type": "way",
      "osm_id": 50637691,
      "boundingbox": [
        "52.3994612",
        "52.3996426",
        "13.0479574",
        "13.0481754"
      ],
      "lat": "52.399550700000006",
      "lon": "13.048066846939687",
      "display_name": "Brandenburger Tor, Brandenburger Straße, Historische Innenstadt, Innenstadt, Potsdam, Brandenburg, 14467, Germany",
      "class": "tourism",
      "type": "attraction",
      "importance": 0.2940287400552381,
      "address": {
        "tourism": "Brandenburger Tor",
        "road": "Brandenburger Straße",
        "suburb": "Historische Innenstadt",
        "city": "Potsdam",
        "state": "Brandenburg",
        "postcode": "14467",
        "country": "Germany",
        "country_code": "de"
      },
      "extratags": {
        "image": "http://commons.wikimedia.org/wiki/File:Potsdam_brandenburger_tor.jpg",
        "heritage": "4",
        "wikidata": "Q695045",
        "architect": "Carl von Gontard;Georg Christian Unger",
        "wikipedia": "de:Brandenburger Tor (Potsdam)",
        "wheelchair": "yes",
        "description": "Kleines Brandenburger Tor in Potsdam",
        "heritage:website": "http://www.bldam-brandenburg.de/images/stories/PDF/DML%202012/04-p-internet-13.pdf",
        "heritage:operator": "bldam",
        "architect:wikidata": "Q68768;Q95223",
        "year_of_construction": "1771"
      }
   }
]
```

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

* `format=[html|xml|json|jsonv2|geojson|geocodejson]`

See [Place Output Formats](Output.md) for details on each format. (Default: xml)

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

[https://nominatim.openstreetmap.org/lookup?osm_ids=R146656,W104393803,N240109189](https://nominatim.openstreetmap.org/lookup?osm_ids=R146656,W104393803,N240109189)

```xml
  <lookupresults timestamp="Mon, 29 Jun 15 18:01:33 +0000" attribution="Data © OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright" querystring="R146656,W104393803,N240109189" polygon="false">
    <place place_id="127761056" osm_type="relation" osm_id="146656" place_rank="16" lat="53.4791466" lon="-2.2447445" display_name="Manchester, Greater Manchester, North West England, England, United Kingdom" class="boundary" type="administrative" importance="0.704893333438333">
      <city>Manchester</city>
      <county>Greater Manchester</county>
      <state_district>North West England</state_district>
      <state>England</state>
      <country>United Kingdom</country>
      <country_code>gb</country_code>
    </place>
    <place place_id="77769745" osm_type="way" osm_id="104393803" place_rank="30" lat="52.5162024" lon="13.3777343363579" display_name="Brandenburg Gate, 1, Pariser Platz, Mitte, Berlin, 10117, Germany" class="tourism" type="attraction" importance="0.443472858361592">
      <attraction>Brandenburg Gate</attraction>
      <house_number>1</house_number>
      <pedestrian>Pariser Platz</pedestrian>
      <suburb>Mitte</suburb>
      <city_district>Mitte</city_district>
      <city>Berlin</city>
      <state>Berlin</state>
      <postcode>10117</postcode>
      <country>Germany</country>
      <country_code>de</country_code>
    </place>
    <place place_id="2570600569" osm_type="node" osm_id="240109189" place_rank="15" lat="52.5170365" lon="13.3888599" display_name="Berlin, Germany" class="place" type="city" importance="0.822149797630868">
      <city>Berlin</city>
      <state>Berlin</state>
      <country>Germany</country>
      <country_code>de</country_code>
    </place>
  </lookupresults>
```

##### JSON with extratags

[https://nominatim.openstreetmap.org/lookup?osm_ids=W50637691&format=json](https://nominatim.openstreetmap.org/lookup?osm_ids=W50637691&format=json)

```json
[
  {
    "place_id": "84271358",
    "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
    "osm_type": "way",
    "osm_id": "50637691",
    "lat": "52.39955055",
    "lon": "13.04806574678",
    "display_name": "Brandenburger Tor, Brandenburger Straße, Nördliche Innenstadt, Innenstadt, Potsdam, Brandenburg, 14467, Germany",
    "class": "historic",
    "type": "city_gate",
    "importance": "0.221233780277011",
    "address": {
      "address29": "Brandenburger Tor",
      "pedestrian": "Brandenburger Straße",
      "suburb": "Nördliche Innenstadt",
      "city": "Potsdam",
      "state": "Brandenburg",
      "postcode": "14467",
      "country": "Germany",
      "country_code": "de"
    },
    "extratags": {
      "image": "http://commons.wikimedia.org/wiki/File:Potsdam_brandenburger_tor.jpg",
      "wikidata": "Q695045",
      "wikipedia": "de:Brandenburger Tor (Potsdam)",
      "wheelchair": "yes",
      "description": "Kleines Brandenburger Tor in Potsdam"
    }
  }
]
```

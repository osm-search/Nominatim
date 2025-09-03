# Address lookup

The lookup API allows to query the address and other details of one or
multiple OSM objects like node, way or relation.

## Endpoint

The lookup API has the following format:

```
  https://nominatim.openstreetmap.org/lookup?osm_ids=[N|W|R]<value>,…,…,&<params>
```

`osm_ids` is mandatory and must contain a comma-separated list of OSM ids each
prefixed with its type, one of node(N), way(W) or relation(R). Up to 50 ids
can be queried at the same time.

!!! danger "Deprecation warning"
    The API can also be used with the URL
    `https://nominatim.openstreetmap.org/lookup.php`. This is now deprecated
    and will be removed in future versions.


## Parameters

This section lists additional optional parameters.

### Output format

| Parameter | Value | Default |
|-----------| ----- | ------- |
| format    | one of: `xml`, `json`, `jsonv2`, `geojson`, `geocodejson` | `jsonv2` |

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
| addressdetails | 0 or 1 | 0 |

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

| Parameter | Value | Default |
|-----------| ----- | ------- |
| entrances | 0 or 1 | 0 |

When set to 1, include the tagged entrances in the result.


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

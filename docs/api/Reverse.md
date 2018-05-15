## Reverse Geocoding

Reverse geocoding generates an address from a latitude and longitude.  The optional `zoom` parameter specifies the level of detail required in terms of something suitable for a Leaflet.js/OpenLayers/etc. zoom level. 

### Parameters
```
https://nominatim.openstreetmap.org/reverse?<query>
```

* `format=[xml|json|jsonv2]`

    * Output format.
    * `jsonv2` adds the next fields to response:
        * `place_rank`
        * `category`
        * `type`
        * `importance`
        * `addresstype`

* `json_callback=<string>`

    * Wrap json output in a callback function (JSONP) i.e. `<string>(<json>)` 

* `accept-language=<browser language string>`

    * Preferred language order for showing search results, overrides the value specified in the "Accept-Language" HTTP header.
    * Either uses standard rfc2616 accept-language string or a simple comma separated list of language codes.

* `osm_type=[N|W|R]` `osm_id=<value>`
    * A specific osm node / way / relation to return an address for
    * **Please use this in preference to lat/lon where possible**

* `lat=<value>` `lon=<value>`
    * The location to generate an address for

* `zoom=[0-18]`
    * Level of detail required where `0` is country and `18` is house/building

* `addressdetails=[0|1]`
    * defaults to 0
    * Include a breakdown of the address into elements

* `email=<valid email address>`

    * If you are making large numbers of request please include a valid email address or alternatively include your email address as part of the User-Agent string.
    * This information will be kept confidential and only used to contact you in the event of a problem, see [Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) for more details.

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

### Example

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

### Hierarchy

* Admin level => XML entity
    * 2 => `<country>`
    * 4 => `<state>`
    * 5 => `<state_district>`
    * 6
    * 7 => `<county>`
    * 8 => `<village>`
    * 9 => `<city_district>`
    * 10 => `<suburb>`

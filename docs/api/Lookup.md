## Address lookup

Lookup the address of one or multiple OSM objects like node, way or relation.

### Parameters
```
  https://nominatim.openstreetmap.org/lookup?<query>
```

* `format=[xml|json]`

    * Output format

* `json_callback=<string>`

    * Wrap json output in a callback function (JSONP) i.e. `<string>(<json>)` 

* `accept-language=<browser language string>`

    * Preferred language order for showing search results, overrides the value specified in the "Accept-Language" HTTP header.
    * Either uses standard rfc2616 accept-language string or a simple comma separated list of language codes.

* `osm_ids=[N|W|R]<value>,…,[N|W|R]<value`
    * A list of up to 50 specific osm node, way or relations ids to return the addresses for

* `addressdetails=[0|1]`
    * defaults to 0
    * Include a breakdown of the address into elements

* `email=<valid email address>`

    * If you are making large numbers of request please include a valid email address or alternatively include your email address as part of the User-Agent string.
    * This information will be kept confidential and only used to contact you in the event of a problem, see [Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) for more details.

* `extratags=1`
    * Include additional information in the result if available, e.g. wikipedia link, opening hours.

* `namedetails=1`
    * Include a list of alternative names in the results.
    * These may include language variants, references, operator and brand.

### Example

* [https://nominatim.openstreetmap.org/lookup?osm_ids=R146656,W104393803,N240109189](https://nominatim.openstreetmap.org/lookup?osm_ids=R146656,W104393803,N240109189)

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

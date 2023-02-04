# Place Output

The [/reverse](Reverse.md), [/search](Search.md) and [/lookup](Lookup.md)
API calls produce very similar output which is explained in this section.
There is one section for each format. The format correspond to what was
selected via the `format` parameter.

## JSON

The JSON format returns an array of places (for search and lookup) or
a single place (for reverse) of the following format:

```
  {
    "place_id": "100149",
    "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
    "osm_type": "node",
    "osm_id": "107775",
    "boundingbox": ["51.3473219", "51.6673219", "-0.2876474", "0.0323526"],
    "lat": "51.5073219",
    "lon": "-0.1276474",
    "display_name": "London, Greater London, England, SW1A 2DU, United Kingdom",
    "class": "place",
    "type": "city",
    "importance": 0.9654895765402,
    "icon": "https://nominatim.openstreetmap.org/images/mapicons/poi_place_city.p.20.png",
    "address": {
      "city": "London",
      "state_district": "Greater London",
      "state": "England",
      "ISO3166-2-lvl4": "GB-ENG",
      "postcode": "SW1A 2DU",
      "country": "United Kingdom",
      "country_code": "gb"
    },
    "extratags": {
      "capital": "yes",
      "website": "http://www.london.gov.uk",
      "wikidata": "Q84",
      "wikipedia": "en:London",
      "population": "8416535"
    }
  }
```

The possible fields are:

 * `place_id` - reference to the Nominatim internal database ID ([see notes](#place_id-is-not-a-persistent-id))
 * `osm_type`, `osm_id` - reference to the OSM object ([see notes](#osm-reference))
 * `boundingbox` - area of corner coordinates ([see notes](#boundingbox))
 * `lat`, `lon` - latitude and longitude of the centroid of the object
 * `display_name` - full comma-separated address
 * `class`, `type` - key and value of the main OSM tag
 * `importance` - computed importance rank
 * `icon` - link to class icon (if available)
 * `address` - dictionary of address details (only with `addressdetails=1`,
   [see notes](#addressdetails))
 * `extratags` - dictionary with additional useful tags like website or maxspeed
   (only with `extratags=1`)
 * `namedetails` - dictionary with full list of available names including ref etc.
 * `geojson`, `svg`, `geotext`, `geokml` - full geometry
   (only with the appropriate `polygon_*` parameter)

## JSONv2

This is the same as the JSON format with two changes:

 * `class` renamed to `category`
 * additional field `place_rank` with the search rank of the object

## GeoJSON

This format follows the [RFC7946](https://geojson.org). Every feature includes
a bounding box (`bbox`).

The properties object has the following fields:

 * `place_id` - reference to the Nominatim internal database ID ([see notes](#place_id-is-not-a-persistent-id))
 * `osm_type`, `osm_id` - reference to the OSM object ([see notes](#osm-reference))
 * `category`, `type` - key and value of the main OSM tag
 * `display_name` - full comma-separated address
 * `place_rank` - class search rank
 * `importance` - computed importance rank
 * `icon` - link to class icon (if available)
 * `address` - dictionary of address details (only with `addressdetails=1`,
   [see notes](#addressdetails))
 * `extratags` - dictionary with additional useful tags like `website` or `maxspeed`
   (only with `extratags=1`)
 * `namedetails` - dictionary with full list of available names including ref etc.

Use `polygon_geojson` to output the full geometry of the object instead
of the centroid.

## GeocodeJSON

The GeocodeJSON format follows the
[GeocodeJSON spec 0.1.0](https://github.com/geocoders/geocodejson-spec).
The following feature attributes are implemented:

 * `osm_type`, `osm_id` - reference to the OSM object (unofficial extension, [see notes](#osm-reference))
 * `type` - the 'address level' of the object ('house', 'street', `district`, `city`,
            `county`, `state`, `country`, `locality`)
 * `osm_key`- key of the main tag of the OSM object (e.g. boundary, highway, amenity)
 * `osm_value` - value of the main tag of the OSM object (e.g. residential, restaurant)
 * `label` - full comma-separated address
 * `name` - localised name of the place
 * `housenumber`, `street`, `locality`, `district`, `postcode`, `city`,
   `county`, `state`, `country` -
   provided when it can be determined from the address
 * `admin` - list of localised names of administrative boundaries (only with `addressdetails=1`)

Use `polygon_geojson` to output the full geometry of the object instead
of the centroid.

## XML

The XML response returns one or more place objects in slightly different
formats depending on the API call.

### Reverse

```
<reversegeocode timestamp="Sat, 11 Aug 18 11:53:21 +0000"
                attribution="Data © OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright"
                querystring="lat=48.400381&lon=11.745876&zoom=5&format=xml">
  <result place_id="179509537" osm_type="relation" osm_id="2145268" ref="BY" place_rank="15" address_rank="15"
          lat="48.9467562" lon="11.4038717"
          boundingbox="47.2701114,50.5647142,8.9763497,13.8396373">
       Bavaria, Germany
  </result>
  <addressparts>
     <state>Bavaria</state>
     <ISO3166-2-lvl4>DE-BY</ISO3166-2-lvl4>
     <country>Germany</country>
     <country_code>de</country_code>
  </addressparts>
  <extratags>
    <tag key="place" value="state"/>
    <tag key="wikidata" value="Q980"/>
    <tag key="wikipedia" value="de:Bayern"/>
    <tag key="population" value="12520000"/>
    <tag key="name:prefix" value="Freistaat"/>
  </extratags>
</reversegeocode>
```

The attributes of the outer `reversegeocode` element return generic information
about the query, including the time when the response was sent (in UTC),
attribution to OSM and the original querystring.

The place information can be found in the `result` element. The attributes of that element contain:

 * `place_id` - reference to the Nominatim internal database ID ([see notes](#place_id-is-not-a-persistent-id))
 * `osm_type`, `osm_id` - reference to the OSM object ([see notes](#osm-reference))
 * `ref` - content of `ref` tag if it exists
 * `lat`, `lon` - latitude and longitude of the centroid of the object
 * `boundingbox` - comma-separated list of corner coordinates ([see notes](#boundingbox))

The full address of the result can be found in the content of the
`result` element as a comma-separated list.

Additional information requested with `addressdetails=1`, `extratags=1` and
`namedetails=1` can be found in extra elements.

### Search and Lookup

```
<searchresults timestamp="Sat, 11 Aug 18 11:55:35 +0000"
               attribution="Data © OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright"
               querystring="london" polygon="false" exclude_place_ids="100149"
               more_url="https://nominatim.openstreetmap.org/search.php?q=london&addressdetails=1&extratags=1&exclude_place_ids=100149&format=xml&accept-language=en-US%2Cen%3Bq%3D0.7%2Cde%3Bq%3D0.3">
  <place place_id="100149" osm_type="node" osm_id="107775" place_rank="15" address_rank="15"
         boundingbox="51.3473219,51.6673219,-0.2876474,0.0323526" lat="51.5073219" lon="-0.1276474"
         display_name="London, Greater London, England, SW1A 2DU, United Kingdom"
         class="place" type="city" importance="0.9654895765402"
         icon="https://nominatim.openstreetmap.org/images/mapicons/poi_place_city.p.20.png">
    <extratags>
      <tag key="capital" value="yes"/>
      <tag key="website" value="http://www.london.gov.uk"/>
      <tag key="wikidata" value="Q84"/>
      <tag key="wikipedia" value="en:London"/>
      <tag key="population" value="8416535"/>
    </extratags>
    <city>London</city>
    <state_district>Greater London</state_district>
    <state>England</state>
    <ISO3166-2-lvl4>GB-ENG</ISO3166-2-lvl4>
    <postcode>SW1A 2DU</postcode>
    <country>United Kingdom</country>
    <country_code>gb</country_code>
  </place>
</searchresults>
```

The attributes of the outer `searchresults` or `lookupresults` element return
generic information about the query:

 * `timestamp` - UTC time when the response was sent
 * `attribution` - OSM licensing information
 * `querystring` - original query
 * `polygon` - true when extra geometry information was requested
 * `exclude_place_ids` - IDs of places that should be ignored in a follow-up request
 * `more_url` - search call that will yield additional results for the query
   just sent

The place information can be found in the `place` elements, of which there may
be more than one. The attributes of that element contain:

 * `place_id` - reference to the Nominatim internal database ID ([see notes](#place_id-is-not-a-persistent-id))
 * `osm_type`, `osm_id` - reference to the OSM object ([see notes](#osm-reference))
 * `ref` - content of `ref` tag if it exists
 * `lat`, `lon` - latitude and longitude of the centroid of the object
 * `boundingbox` - comma-separated list of corner coordinates ([see notes](#boundingbox))
 * `place_rank` - class [search rank](../customize/Ranking.md#search-rank)
 * `address_rank` - place [address rank](../customize/Ranking.md#address-rank)
 * `display_name` - full comma-separated address
 * `class`, `type` - key and value of the main OSM tag
 * `importance` - computed importance rank
 * `icon` - link to class icon (if available)

When `addressdetails=1` is requested, the localised address parts appear
as subelements with the type of the address part.

Additional information requested with `extratags=1` and `namedetails=1` can
be found in extra elements as sub-element of `extratags` and `namedetails`
respectively.


## Notes on field values

### place_id is not a persistent id

The `place_id` is an internal identifier that is assigned data is imported
into a Nominatim database. The same OSM object will have a different value
on another server. It may even change its ID on the same server when it is
removed and reimported while updating the database with fresh OSM data.
It is thus not useful to treat it as permanent for later use.

The combination `osm_type`+`osm_id` is slightly better but remember in
OpenStreetMap mappers can delete, split, recreate places (and those
get a new `osm_id`), there is no link between those old and new ids.
Places can also change their meaning without changing their `osm_id`,
e.g. when a restaurant is retagged as supermarket. For a more in-depth
discussion see [Permanent ID](https://wiki.openstreetmap.org/wiki/Permanent_ID).

If you need an ID that is consistent over multiple installations of Nominatim,
then you should use the combination of `osm_type`+`osm_id`+`class`.

### OSM reference

Nominatim may sometimes return special objects that do not correspond directly
to an object in OpenStreetMap. These are:

* **Postcodes**. Nominatim returns an postcode point created from all mapped
  postcodes of the same name. The class and type of these object is `place=postcdode`.
  No `osm_type` and `osm_id` are included in the result.
* **Housenumber interpolations**. Nominatim returns a single interpolated
  housenumber from the interpolation way. The class and type are `place=house`
  and `osm_type` and `osm_id` correspond to the interpolation way in OSM.
* **TIGER housenumber.** Nominatim returns a single interpolated housenumber
  from the TIGER data. The class and type are `place=house`
  and `osm_type` and `osm_id` correspond to the street mentioned in the result.

Please note that the `osm_type` and `osm_id` returned may be changed in the
future. You should not expect to only find `node`, `way` and `relation` for
the type.

### boundingbox

Comma separated list of min latitude, max latitude, min longitude, max longitude.
The whole planet would be `-90,90,-180,180`.

Can be used to pan and center the map on the result, for example with leafletjs
mapping library
`map.fitBounds([[bbox[0],bbox[2]],[bbox[1],bbox[3]]], {padding: [20, 20], maxzoom: 16});`

Bounds crossing the antimeridian have a min latitude -180 and max latitude 180,
essentially covering the entire planet
(see [issue 184](https://github.com/openstreetmap/Nominatim/issues/184)).

### addressdetails

Address details in the xml and json formats return a list of names together
with a designation label. Per default the following labels may appear:

 * continent
 * country, country_code
 * region, state, state_district, county, ISO3166-2-lvl<admin_level>
 * municipality, city, town, village
 * city_district, district, borough, suburb, subdivision
 * hamlet, croft, isolated_dwelling
 * neighbourhood, allotments, quarter
 * city_block, residential, farm, farmyard, industrial, commercial, retail
 * road
 * house_number, house_name
 * emergency, historic, military, natural, landuse, place, railway,
   man_made, aerialway, boundary, amenity, aeroway, club, craft, leisure,
   office, mountain_pass, shop, tourism, bridge, tunnel, waterway
 * postcode

They roughly correspond to the classification of the OpenStreetMap data
according to either the `place` tag or the main key of the object.

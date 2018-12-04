# Place Output

The [\reverse](Reverse.md), [\search](Search.md) and [\lookup](Lookup.md)
API calls produce very similar output which is explained in this section.
There is one section for each format which is selectable via the `format`
parameter.

## Formats

### JSON

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
  },
```

The possible fields are:

 * `place_id` - reference to the Nominatim internal database ID (see notes below)
 * `osm_type`, `osm_id` - reference to the OSM object
 * `boundingbox` - area of corner coordinates
 * `lat`, `lon` - latitude and longitude of the centroid of the object
 * `display_name` - full comma-separated address
 * `class`, `type` - key and value of the main OSM tag
 * `importance` - computed importance rank
 * `icon` - link to class icon (if available)
 * `address` - dictionary of address details (only with `addressdetails=1`)
 * `extratags` - dictionary with additional useful tags like website or maxspeed
   (only with `extratags=1`)
 * `namedetails` - dictionary with full list of available names including ref etc.
 * `geojson`, `svg`, `geotext`, `geokml` - full geometry
   (only with the appropriate `polygon_*` parameter)

### JSONv2

This is the same as the JSON format with two changes:

 * `class` renamed to `category`
 * additional field `place_rank` with the search rank of the object

### GeoJSON

This format follows the [RFC7946](http://geojson.org). Every feature includes
a bounding box (`bbox`).

The feature list has the following fields:

 * `place_id` - reference to the Nominatim internal database ID (see notes below)
 * `osm_type`, `osm_id` - reference to the OSM object
 * `category`, `type` - key and value of the main OSM tag
 * `display_name` - full comma-separated address
 * `place_rank` - class search rank
 * `importance` - computed importance rank
 * `icon` - link to class icon (if available)
 * `address` - dictionary of address details (only with `addressdetails=1`)
 * `extratags` - dictionary with additional useful tags like website or maxspeed
   (only with `extratags=1`)
 * `namedetails` - dictionary with full list of available names including ref etc.

Use `polygon_geojson` to output the full geometry of the object instead
of the centroid.

### GeocodeJSON

The GeocodeJSON format follows the
[GeocodeJSON spec 0.1.0](https://github.com/geocoders/geocodejson-spec).
The following feature attributes are implemented:

 * `osm_type`, `osm_id` - reference to the OSM object (unofficial extension)
 * `type` - value of the main tag of the object (e.g. residential, restaurant, ...)
 * `label` - full comma-separated address
 * `name` - localised name of the place
 * `housenumber`, `street`, `locality`, `postcode`, `city`,
   `district`, `county`, `state`, `country` -
   provided when it can be determined from the address
   (see [this issue](https://github.com/openstreetmap/Nominatim/issues/1080) for
   current limitations on the correctness of the address) and `addressdetails=1`
   was given
 * `admin` - list of localised names of administrative boundaries (only with `addressdetails=1`)

Use `polygon_geojson` to output the full geometry of the object instead
of the centroid.

### XML

The XML response returns one or more place objects in slightly different
formats depending on the API call.

#### Reverse

```
<reversegeocode timestamp="Sat, 11 Aug 18 11:53:21 +0000"
                attribution="Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright"
                querystring="lat=48.400381&lon=11.745876&zoom=5&format=xml">
  <result place_id="179509537" osm_type="relation" osm_id="2145268" ref="BY"
          lat="48.9467562" lon="11.4038717"
          boundingbox="47.2701114,50.5647142,8.9763497,13.8396373">
       Bavaria, Germany
  </result>
  <addressparts>
     <state>Bavaria</state>
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

 * `place_id` - reference to the Nominatim internal database ID (see notes below)
 * `osm_type`, `osm_id` - reference to the OSM object
 * `ref` - content of `ref` tag if it exists
 * `lat`, `lon` - latitude and longitude of the centroid of the object
 * `boundingbox` - comma-separated list of corner coordinates

The full address address of the result can be found in the content of the
`result` element as a comma-separated list.

Additional information requested with `addressdetails=1`, `extratags=1` and
`namedetails=1` can be found in extra elements.

#### Search and Lookup

```
<searchresults timestamp="Sat, 11 Aug 18 11:55:35 +0000"
               attribution="Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright"
               querystring="london" polygon="false" exclude_place_ids="100149"
               more_url="https://nominatim.openstreetmap.org/search.php?q=london&addressdetails=1&extratags=1&exclude_place_ids=100149&format=xml&accept-language=en-US%2Cen%3Bq%3D0.7%2Cde%3Bq%3D0.3">
  <place place_id="100149" osm_type="node" osm_id="107775" place_rank="15"
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

 * `place_id` - reference to the Nominatim internal database ID (see notes below)
 * `osm_type`, `osm_id` - reference to the OSM object
 * `ref` - content of `ref` tag if it exists
 * `lat`, `lon` - latitude and longitude of the centroid of the object
 * `boundingbox` - comma-separated list of corner coordinates
 * `place_rank` - class search rank
 * `display_name` - full comma-separated address
 * `class`, `type` - key and value of the main OSM tag
 * `importance` - computed importance rank
 * `icon` - link to class icon (if available)

When `addressdetails=1` is requested, the localised address parts appear
as subelements with the type of the address part.

Additional information requested with `extratags=1` and `namedetails=1` can
be found in extra elements as sub-element of each place.


## Notes on field values

### place_id is not a persistent id

The `place_id` is created when a Nominatim database gets installed. A
single place will have a different value on another server or even when
the same data gets re-imported. It's thus not useful to treat it as
permanent for later use.

The combination `osm_type`+`osm_id` is slighly better but remember in
OpenStreetMap mappers can delete, split, recreate places (and those
get a new `osm_id`), there is no link between those old and new id.
Places can also change their meaning without changing their `osm_id`,
e.g. when a restaurant is retagged as supermarket. For a more in-depth
discussion see [Permanent ID](https://wiki.openstreetmap.org/wiki/Permanent_ID).

Nominatim merges some places (e.g. center node of a city with the boundary
relation) so `osm_type`+`osm_id`+`class_name` would be more unique.

### boundingbox

Comma separated list of min latitude, max latitude, min longitude, max longitude.
The whole planet would be `-90,90,-180,180`.

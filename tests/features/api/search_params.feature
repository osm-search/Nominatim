Feature: Search queries
    Testing different queries and parameters

    Scenario: Simple XML search
        When sending xml search query "Schaan"
        Then result 0 has attributes place_id,osm_type,osm_id
        And result 0 has attributes place_rank,boundingbox
        And result 0 has attributes lat,lon,display_name
        And result 0 has attributes class,type,importance,icon
        And result 0 has not attributes address
        And results contain valid boundingboxes

    Scenario: Simple JSON search
        When sending json search query "Vaduz"
        And result 0 has attributes place_id,licence,icon,class,type
        And result 0 has attributes osm_type,osm_id,boundingbox
        And result 0 has attributes lat,lon,display_name,importance
        And result 0 has not attributes address
        And results contain valid boundingboxes

    Scenario: JSON search with addressdetails
        When sending json search query "Montevideo" with address
        Then address of result 0 is
          | type         | value
          | city         | Montevideo
          | state        | Montevideo
          | country      | Uruguay
          | country_code | uy

    Scenario: XML search with addressdetails
        When sending xml search query "Inuvik" with address
        Then address of result 0 contains
          | type         | value
          | state        | Northwest Territories
          | country      | Canada
          | country_code | ca

    Scenario: Address details with unknown class types
        When sending json search query "foobar, Essen" with address
        Then results contain
          | ID | class   | type
          | 0  | leisure | hackerspace
        And result addresses contain
          | ID | address29
          | 0  | Chaospott
        And address of result 0 does not contain leisure,hackerspace

    Scenario: Disabling deduplication
        When sending json search query "Oxford Street, London"
        Then there are no duplicates
        Given the request parameters
          | dedupe
          | 0
        When sending json search query "Oxford Street, London"
        Then there are duplicates

    Scenario: Search with bounded viewbox in right area
        Given the request parameters
          | bounded | viewbox
          | 1       | -87.7,41.9,-87.57,41.85
        When sending json search query "restaurant" with address
        Then result addresses contain
          | ID | city
          | 0  | Chicago

    Scenario: Search with bounded viewboxlbrt in right area
        Given the request parameters
          | bounded | viewboxlbrt
          | 1       | -87.7,41.85,-87.57,41.9
        When sending json search query "restaurant" with address
        Then result addresses contain
          | ID | city
          | 0  | Chicago

    Scenario: No POI search with unbounded viewbox
        Given the request parameters
          | viewbox
          | -87.7,41.9,-87.57,41.85
        When sending json search query "restaurant"
        Then results contain
          | display_name
          | [^,]*(?i)restaurant.*

    Scenario: bounded search remains within viewbox, even with no results
        Given the request parameters
         | bounded | viewbox
         | 1       | 43.54285,-5.662003,43.5403125,-5.6563282
         When sending json search query "restaurant"
        Then less than 1 result is returned

    Scenario: bounded search remains within viewbox with results
        Given the request parameters
         | bounded | viewbox
         | 1       | -5.662003,43.55,-5.6563282,43.5403125
        When sending json search query "restaurant"
         | lon          | lat
         | >= -5.662003 | >= 43.5403125
         | <= -5.6563282| <= 43.55

    Scenario: Prefer results within viewbox
        Given the request parameters
          | accept-language
          | en
        When sending json search query "royan" with address
        Then result addresses contain
          | ID | country
          | 0  | France
        Given the request parameters
          | accept-language | viewbox
          | en              | 51.94,36.59,51.99,36.56
        When sending json search query "royan" with address
        Then result addresses contain
          | ID | country
          | 0  | Iran

    Scenario: Overly large limit number for search results
        Given the request parameters
          | limit
          | 1000
        When sending json search query "Neustadt"
        Then at most 50 results are returned

    Scenario: Limit number of search results
        Given the request parameters
          | limit
          | 4
        When sending json search query "Neustadt"
        Then exactly 4 results are returned

    Scenario: Restrict to feature type country
        Given the request parameters
          | featureType
          | country
        When sending xml search query "Monaco"
        Then results contain
          | place_rank
          | 4

    Scenario: Restrict to feature type state
        When sending xml search query "Berlin"
        Then results contain
          | ID | place_rank
          | 0  | 1[56]
        Given the request parameters
          | featureType
          | state
        When sending xml search query "Berlin"
        Then results contain
          | place_rank
          | [78]

    Scenario: Restrict to feature type city
        Given the request parameters
          | featureType
          | city
        When sending xml search query "Monaco"
        Then results contain
          | place_rank
          | 1[56789]


    Scenario: Restrict to feature type settlement
        When sending json search query "Everest"
        Then results contain
          | ID | display_name
          | 0  | Mount Everest.*
        Given the request parameters
          | featureType
          | settlement
        When sending json search query "Everest"
        Then results contain
          | ID | display_name
          | 0  | Everest.*

    Scenario Outline: Search with polygon threshold (json)
        Given the request parameters
          | polygon_geojson | polygon_threshold
          | 1               | <th>
        When sending json search query "switzerland"
        Then at least 1 result is returned
        And result 0 has attributes geojson

     Examples:
        | th
        | -1
        | 0.0
        | 0.5
        | 999

    Scenario Outline: Search with polygon threshold (xml)
        Given the request parameters
          | polygon_geojson | polygon_threshold
          | 1               | <th>
        When sending xml search query "switzerland"
        Then at least 1 result is returned
        And result 0 has attributes geojson

     Examples:
        | th
        | -1
        | 0.0
        | 0.5
        | 999

    Scenario Outline: Search with invalid polygon threshold (xml)
        Given the request parameters
          | polygon_geojson | polygon_threshold
          | 1               | <th>
        When sending xml search query "switzerland"
        Then a HTTP 400 is returned


    Scenario Outline: Search with extratags
        Given the request parameters
          | extratags
          | 1
        When sending <format> search query "Hauptstr"
        Then result 0 has attributes extratags
        And result 1 has attributes extratags

    Examples:
        | format
        | xml
        | json
        | jsonv2

    Scenario Outline: Search with namedetails
        Given the request parameters
          | namedetails
          | 1
        When sending <format> search query "Hauptstr"
        Then result 0 has attributes namedetails
        And result 1 has attributes namedetails

    Examples:
        | format
        | xml
        | json
        | jsonv2


   Scenario Outline: Search result with contains TEXT geometry
        Given the request parameters
          | polygon_text
          | 1
        When sending <format> search query "switzerland"
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geotext
        | json     | geotext
        | jsonv2   | geotext

   Scenario Outline: Search result contains polygon-as-points geometry
        Given the request parameters
          | polygon
          | 1
        When sending <format> search query "switzerland"
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | polygonpoints
        | json     | polygonpoints
        | jsonv2   | polygonpoints



   Scenario Outline: Search result contains SVG geometry
        Given the request parameters
          | polygon_svg
          | 1
        When sending <format> search query "switzerland"
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geosvg
        | json     | svg
        | jsonv2   | svg


   Scenario Outline: Search result contains KML geometry
        Given the request parameters
          | polygon_kml
          | 1
        When sending <format> search query "switzerland"
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geokml
        | json     | geokml
        | jsonv2   | geokml


   Scenario Outline: Search result contains GEOJSON geometry
        Given the request parameters
          | polygon_geojson
          | 1
        When sending <format> search query "switzerland"
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geojson
        | json     | geojson
        | jsonv2   | geojson

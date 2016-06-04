Feature: Reverse geocoding
    Testing the reverse function

    # Make sure country is not overwritten by the postcode
    Scenario: Country is returned
        Given the request parameters
          | accept-language
          | de
        When looking up coordinates 53.9788769,13.0830313
        Then result addresses contain 
         | ID | country
         | 0  | Deutschland


    Scenario: Boundingbox is returned
        Given the request parameters
          | format | zoom
          | xml    | 4
        When looking up coordinates 53.9788769,13.0830313
        And results contain valid boundingboxes
    
    Scenario: Reverse geocoding for odd interpolated housenumber
    
    Scenario: Reverse geocoding for even interpolated housenumber

    @Tiger
    Scenario: TIGER house number
        Given the request parameters
          | addressdetails
          | 1
        When looking up coordinates 40.6863624710666,-112.060005720023
        And exactly 1 result is returned
        And result addresses contain
          | ID | house_number | road               | postcode | country_code
          | 0  | 7096         | Kings Estate Drive | 84128    | us
        And result 0 has not attributes osm_id,osm_type


    @Tiger
    Scenario: No TIGER house number for zoom < 18
        Given the request parameters
          | addressdetails | zoom
          | 1              | 17
        When looking up coordinates 40.6863624710666,-112.060005720023
        And exactly 1 result is returned
        And result addresses contain
          | ID | road               | postcode | country_code
          | 0  | Kings Estate Drive | 84128    | us
        And result 0 has attributes osm_id,osm_type

   Scenario Outline: Reverse Geocoding with extratags
        Given the request parameters
          | extratags
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes extratags

   Examples:
        | format
        | xml
        | json
        | jsonv2

   Scenario Outline: Reverse Geocoding with namedetails
        Given the request parameters
          | namedetails
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes namedetails

   Examples:
        | format
        | xml
        | json
        | jsonv2


   Scenario Outline: Reverse Geocoding contains TEXT geometry
        Given the request parameters
          | polygon_text
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geotext
        | json     | geotext
        | jsonv2   | geotext

   Scenario Outline: Reverse Geocoding contains polygon-as-points geometry
        Given the request parameters
          | polygon
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has not attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | polygonpoints
        | json     | polygonpoints
        | jsonv2   | polygonpoints



   Scenario Outline: Reverse Geocoding contains SVG geometry
        Given the request parameters
          | polygon_svg
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geosvg
        | json     | svg
        | jsonv2   | svg


   Scenario Outline: Reverse Geocoding contains KML geometry
        Given the request parameters
          | polygon_kml
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geokml
        | json     | geokml
        | jsonv2   | geokml


   Scenario Outline: Reverse Geocoding contains GEOJSON geometry
        Given the request parameters
          | polygon_geojson
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes <response_attribute>

   Examples:
        | format   | response_attribute
        | xml      | geojson
        | json     | geojson
        | jsonv2   | geojson



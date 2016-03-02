Feature: Simple Reverse Tests
    Simple tests for internal server errors and response format.
    These tests should pass on any Nominatim installation.

    Scenario Outline: Simple reverse-geocoding
        When looking up xml coordinates <lat>,<lon>
        Then the result is valid xml
        When looking up json coordinates <lat>,<lon>
        Then the result is valid json
        When looking up jsonv2 coordinates <lat>,<lon>
        Then the result is valid json

    Examples:
     | lat      | lon
     | 0.0      | 0.0
     | 45.3     | 3.5
     | -79.34   | 23.5
     | 0.23     | -178.555

    Scenario Outline: Testing different parameters
        Given the request parameters
          | <parameter>
          | <value>
        When sending search query "Manchester"
        Then the result is valid html
        Given the request parameters
          | <parameter>
          | <value>
        When sending html search query "Manchester"
        Then the result is valid html
        Given the request parameters
          | <parameter>
          | <value>
        When sending xml search query "Manchester"
        Then the result is valid xml
        Given the request parameters
          | <parameter>
          | <value>
        When sending json search query "Manchester"
        Then the result is valid json
        Given the request parameters
          | <parameter>
          | <value>
        When sending jsonv2 search query "Manchester"
        Then the result is valid json

    Examples:
     | parameter        | value
     | polygon          | 1
     | polygon          | 0
     | polygon_text     | 1
     | polygon_text     | 0
     | polygon_kml      | 1
     | polygon_kml      | 0
     | polygon_geojson  | 1
     | polygon_geojson  | 0
     | polygon_svg      | 1
     | polygon_svg      | 0




    Scenario Outline: Wrapping of legal jsonp requests
        Given the request parameters
        | json_callback
        | foo
        When looking up <format> coordinates 67.3245,0.456
        Then the result is valid json

    Examples:
      | format
      | json
      | jsonv2

    Scenario: Reverse-geocoding without address
        Given the request parameters
          | addressdetails
          | 0
        When looking up xml coordinates 36.791966,127.171726
        Then the result is valid xml
        When looking up json coordinates 36.791966,127.171726
        Then the result is valid json
        When looking up jsonv2 coordinates 36.791966,127.171726
        Then the result is valid json

    Scenario: Reverse-geocoding with zoom
        Given the request parameters
          | zoom
          | 10
        When looking up xml coordinates 36.791966,127.171726
        Then the result is valid xml
        When looking up json coordinates 36.791966,127.171726
        Then the result is valid json
        When looking up jsonv2 coordinates 36.791966,127.171726
        Then the result is valid json

    Scenario: Missing lon parameter
        Given the request parameters
          | lat
          | 51.51
        When sending an API call reverse
        Then exactly 0 results are returned

    Scenario: Missing lat parameter
        Given the request parameters
          | lon
          | -79.39114
        When sending an API call reverse
        Then exactly 0 results are returned

    Scenario: Missing osm_id parameter
        Given the request parameters
          | osm_type
          | N
        When sending an API call reverse
        Then exactly 0 results are returned

    Scenario: Missing osm_type parameter
        Given the request parameters
          | osm_id
          | 3498564
        When sending an API call reverse
        Then exactly 0 results are returned

    Scenario Outline: Bad format for lat or lon
        Given the request parameters
          | lat   | lon   |
          | <lat> | <lon> |
        When sending an API call reverse
        Then exactly 0 results are returned

    Examples:
     | lat      | lon
     | 48.9660  | 8,4482
     | 48,9660  | 8.4482
     | 48,9660  | 8,4482
     | 48.966.0 | 8.4482
     | 48.966   | 8.448.2
     | Nan      | 8.448
     | 48.966   | Nan
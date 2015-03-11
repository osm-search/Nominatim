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

    Scenario: address lookup for existing node, way, relation
        When looking up xml looking up places N158845944,W72493656,R62422
        Then the result is valid xml
        When looking up json looking up places N158845944,W72493656,R62422
        Then the result is valid json

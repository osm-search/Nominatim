@APIDB
Feature: Simple Reverse Tests
    Simple tests for internal server errors and response format.

    Scenario Outline: Simple reverse-geocoding
        When sending reverse coordinates <lat>,<lon>
        Then the result is valid xml
        When sending xml reverse coordinates <lat>,<lon>
        Then the result is valid xml
        When sending json reverse coordinates <lat>,<lon>
        Then the result is valid json
        When sending jsonv2 reverse coordinates <lat>,<lon>
        Then the result is valid json
        When sending geojson reverse coordinates <lat>,<lon>
        Then the result is valid geojson
        When sending html reverse coordinates <lat>,<lon>
        Then the result is valid html

    Examples:
     | lat      | lon |
     | 0.0      | 0.0 |
     | -34.830  | -56.105 |
     | 45.174   | -103.072 |
     | 21.156   | -12.2744 |

    Scenario Outline: Testing different parameters
        When sending reverse coordinates 53.603,10.041
          | param       | value   |
          | <parameter> | <value> |
        Then the result is valid xml
        When sending html reverse coordinates 53.603,10.041
          | param       | value   |
          | <parameter> | <value> |
        Then the result is valid html
        When sending xml reverse coordinates 53.603,10.041
          | param       | value   |
          | <parameter> | <value> |
        Then the result is valid xml
        When sending json reverse coordinates 53.603,10.041
          | param       | value   |
          | <parameter> | <value> |
        Then the result is valid json
        When sending jsonv2 reverse coordinates 53.603,10.041
          | param       | value   |
          | <parameter> | <value> |
        Then the result is valid json
        When sending geojson reverse coordinates 53.603,10.041
          | param       | value   |
          | <parameter> | <value> |
        Then the result is valid geojson
        When sending geocodejson reverse coordinates 53.603,10.041
          | param       | value   |
          | <parameter> | <value> |
        Then the result is valid geocodejson

    Examples:
     | parameter        | value |
     | polygon_text     | 1 |
     | polygon_text     | 0 |
     | polygon_kml      | 1 |
     | polygon_kml      | 0 |
     | polygon_geojson  | 1 |
     | polygon_geojson  | 0 |
     | polygon_svg      | 1 |
     | polygon_svg      | 0 |

    Scenario Outline: Wrapping of legal jsonp requests
        When sending <format> reverse coordinates 67.3245,0.456
        | json_callback |
        | foo |
        Then the result is valid <outformat>

    Examples:
      | format | outformat |
      | json | json |
      | jsonv2 | json |
      | geojson | geojson |

    Scenario Outline: Boundingbox is returned
        When sending <format> reverse coordinates 14.62,108.1
          | zoom |
          | 8 |
        Then result has bounding box in 9,20,102,113

    Examples:
      | format |
      | json |
      | jsonv2 |
      | geojson |
      | xml |

    Scenario Outline: Reverse-geocoding with zoom
        When sending <format> reverse coordinates 53.603,10.041
          | zoom |
          | 10 |
        Then exactly 1 result is returned

    Examples:
      | format |
      | json |
      | jsonv2 |
      | geojson |
      | html |
      | xml |

    Scenario: Missing lon parameter
        When sending reverse coordinates 52.52,
        Then a HTTP 400 is returned

    Scenario: Missing lat parameter
        When sending reverse coordinates ,52.52
        Then a HTTP 400 is returned

    Scenario: Missing osm_id parameter
        When sending reverse coordinates ,
          | osm_type |
          | N |
        Then a HTTP 400 is returned

    Scenario: Missing osm_type parameter
        When sending reverse coordinates ,
          | osm_id |
          | 3498564 |
        Then a HTTP 400 is returned

    Scenario Outline: Bad format for lat or lon
        When sending reverse coordinates ,
          | lat   | lon   |
          | <lat> | <lon> |
        Then a HTTP 400 is returned

    Examples:
     | lat      | lon |
     | 48.9660  | 8,4482 |
     | 48,9660  | 8.4482 |
     | 48,9660  | 8,4482 |
     | 48.966.0 | 8.4482 |
     | 48.966   | 8.448.2 |
     | Nan      | 8.448 |
     | 48.966   | Nan |

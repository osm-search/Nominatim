Feature: XML output for Reverse API
    Testing correctness of xml output (API version v1).

    Scenario Outline: Reverse XML - Simple reverse-geocoding with no results
        When sending v1/reverse
          | lat   | lon   |
          | <lat> | <lon> |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result has no attributes osm_type, address, extratags
        And the result contains
          | error |
          | Unable to geocode |

        Examples:
         | lat      | lon |
         | 0.0      | 0.0 |
         | 91.3     | 0.4    |
         | -700     | 0.4    |
         | 0.2      | 324.44 |
         | 0.2      | -180.4 |

    Scenario Outline: Reverse XML - OSM result with and without addresses
        When sending v1/reverse with format xml
          | lat    | lon   | addressdetails |
          | 47.066 | 9.504 | <has_address>  |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result has attributes place_id
        And the result has <attributes> address
        And the result contains
          | osm_type | osm_id     | place_rank | address_rank |
          | node     | 6522627624 | 30         | 30           |
        And the result contains
          | lon       | lat        | boundingbox |
          | 9.5036065 | 47.0660892 | 47.0660392,47.0661392,9.5035565,9.5036565 |
        And the result contains
          | ref                   | display_name |
          | Dorfbäckerei Herrmann | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |

        Examples:
          | has_address | attributes     |
          | 1           | attributes     |
          | 0           | no attributes |

    Scenario: Reverse XML - Tiger address
        When sending v1/reverse with format xml
          | lat           | lon            |
          | 32.4752389363 | -86.4810198619 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | osm_type | osm_id    | place_rank  | address_rank |
          | way      | 396009653 | 30          | 30           |
        And the result contains
          | lon         | lat        | boundingbox |
          | -86.4808553 | 32.4753580 | 32.4753080,32.4754080,-86.4809053,-86.4808053 |
        And the result contains
          | display_name |
          | 707, Upper Kingston Road, Upper Kingston, Prattville, Autauga County, 36067, United States |

    Scenario: Reverse XML - Interpolation address
        When sending v1/reverse with format xml
          | lat       | lon        |
          | 47.118533 | 9.57056562 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | osm_type | osm_id | place_rank | address_rank |
          | way      | 1      | 30         | 30           |
        And the result contains
          | lon       | lat        | boundingbox |
          | 9.5705468 | 47.1185454 | 47.1184954,47.1185954,9.5704968,9.5705968 |
        And the result contains
          | display_name |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

    Scenario: Reverse XML - Output of geojson
        When sending v1/reverse with format xml
          | lat      | lon     | polygon_geojson |
          | 47.06597 | 9.50467 | 1               |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | geojson |
          | {"type":"LineString","coordinates":[[9.5039353,47.0657546],[9.5040437,47.0657781],[9.5040808,47.065787],[9.5054298,47.0661407]]}  |

    Scenario: Reverse XML - Output of WKT
        When sending v1/reverse with format xml
          | lat      | lon     | polygon_text |
          | 47.06597 | 9.50467 | 1            |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | geotext!fm |
          | LINESTRING\(9.5039353 47.0657546, ?9.5040437 47.0657781, ?9.5040808 47.065787, ?9.5054298 47.0661407\) |

    Scenario: Reverse XML - Output of SVG
        When sending v1/reverse with format xml
          | lat      | lon     | polygon_svg |
          | 47.06597 | 9.50467 | 1           |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | geosvg |
          | M 9.5039353 -47.0657546 L 9.5040437 -47.0657781 9.5040808 -47.065787 9.5054298 -47.0661407 |

    Scenario: Reverse XML - Output of KML
       When sending v1/reverse with format xml
          | lat      | lon     | polygon_kml |
          | 47.06597 | 9.50467 | 1           |
        Then a HTTP 200 is returned
        And the result is valid xml
       And the result contains
          | geokml!fm |
          | <geokml><LineString><coordinates>9.5039\d*,47.0657\d* 9.5040\d*,47.0657\d* 9.5040\d*,47.065\d* 9.5054\d*,47.0661\d*</coordinates></LineString></geokml> |

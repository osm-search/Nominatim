Feature: Json output for Reverse API
    Testing correctness of json and jsonv2 output (API version v1).

    Scenario Outline: Reverse json - Simple with no results
        When sending v1/reverse with format json
          | lat   | lon   |
          | <lat> | <lon> |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | error |
          | Unable to geocode |
        When sending v1/reverse with format jsonv2
          | lat   | lon   |
          | <lat> | <lon> |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | error |
          | Unable to geocode |

        Examples:
          | lat  | lon |
          | 0.0  | 0.0 |
          | 91.3 | 0.4    |
          | -700 | 0.4    |
          | 0.2  | 324.44 |
          | 0.2  | -180.4 |

    Scenario Outline: Reverse json - OSM result with and without addresses
        When sending v1/reverse with format json
          | lat    | lon   | addressdetails |
          | 47.066 | 9.504 | <has_address>  |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has <attributes> address
        When sending v1/reverse with format jsonv2
          | lat    | lon   | addressdetails |
          | 47.066 | 9.504 | <has_address>  |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has <attributes> address

        Examples:
          | has_address | attributes    |
          | 1           | attributes    |
          | 0           | no attributes |

    Scenario Outline: Reverse json - Simple OSM result
        When sending v1/reverse with format <format>
          | lat    | lon   |
          | 47.066 | 9.504 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes place_id
        And the result contains
          | licence!fm |
          | Data © OpenStreetMap contributors, ODbL 1.0. https?://osm.org/copyright |
        And the result contains
          | osm_type | osm_id     |
          | node     | 6522627624 |
        And the result contains
          | lon       | lat        | boundingbox!in_box |
          | 9.5036065 | 47.0660892 | 47.0660391, 47.0661393, 9.5035564, 9.5036566 |
        And the result contains
          | display_name |
          | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |
        And the result has no attributes namedetails,extratags

        Examples:
          | format |
          | json   |
          | jsonv2 |

    Scenario: Reverse json - Extra attributes of jsonv2 result
        When sending v1/reverse with format jsonv2
          | lat    | lon   |
          | 47.066 | 9.504 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes importance
        And the result contains
          | category | type   | name                  | place_rank | addresstype |
          | shop     | bakery | Dorfbäckerei Herrmann | 30         | shop        |

    Scenario: Reverse json - Tiger address
        When sending v1/reverse with format jsonv2
          | lat           | lon            |
          | 32.4752389363 | -86.4810198619 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | osm_type | osm_id    | category | type  | addresstype  |
          | way      | 396009653 | place    | house | place        |

    Scenario Outline: Reverse json - Interpolation address
        When sending v1/reverse with format <format>
          | lat       | lon        |
          | 47.118533 | 9.57056562 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | osm_type | osm_id |
          | way      | 1      |
        And the result contains
          | lon       | lat        | boundingbox!in_box |
          | 9.5705467 | 47.1185454 | 47.118494, 47.118596, 9.570495, 9.570597 |
        And the result contains
          | display_name |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

        Examples:
          | format |
          | json   |
          | jsonv2 |

    Scenario Outline: Reverse json - Output of geojson
        When sending v1/reverse with format <format>
          | lat      | lon     | polygon_geojson |
          | 47.06597 | 9.50467 | 1               |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | geojson+type | geojson+coordinates |
          | LineString   | [[9.5039353, 47.0657546], [9.5040437, 47.0657781], [9.5040808, 47.065787], [9.5054298, 47.0661407]] |

       Examples:
          | format |
          | json   |
          | jsonv2 |

    Scenario Outline: Reverse json - Output of WKT
        When sending v1/reverse with format <format>
          | lat      | lon     | polygon_text |
          | 47.06597 | 9.50467 | 1            |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | geotext!wkt |
          | 9.5039353 47.0657546, 9.5040437 47.0657781, 9.5040808 47.065787, 9.5054298 47.0661407 |

       Examples:
          | format |
          | json   |
          | jsonv2 |

    Scenario Outline: Reverse json - Output of SVG
       When sending v1/reverse with format <format>
          | lat      | lon     | polygon_svg |
          | 47.06597 | 9.50467 | 1           |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | svg |
          | M 9.5039353 -47.0657546 L 9.5040437 -47.0657781 9.5040808 -47.065787 9.5054298 -47.0661407 |

       Examples:
          | format |
          | json   |
          | jsonv2 |

    Scenario Outline: Reverse json - Output of KML
        When sending v1/reverse with format <format>
          | lat      | lon     | polygon_kml |
          | 47.06597 | 9.50467 | 1           |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | geokml!fm |
          | <LineString><coordinates>9.5039\d*,47.0657\d* 9.5040\d*,47.0657\d* 9.5040\d*,47.065\d* 9.5054\d*,47.0661\d*</coordinates></LineString> |

       Examples:
          | format |
          | json   |
          | jsonv2 |

Feature: Geojson for Reverse API
    Testing correctness of geojson output (API version v1).

    Scenario Outline: Reverse geojson - Simple with no results
        When sending v1/reverse with format geojson
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

    Scenario Outline: Reverse geojson - Simple OSM result
        When sending v1/reverse with format geojson
          | lat    | lon   | addressdetails |
          | 47.066 | 9.504 | <has_address>  |
        Then a HTTP 200 is returned
        And the result is valid geojson with 1 result
        And the result metadata contains
          | licence!fm |
          | Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright |
        And all results have attributes place_id, importance
        And all results have <attributes> address
        And all results contain
          | param               | value |
          | osm_type            | node |
          | osm_id              | 6522627624 |
          | place_rank          | 30 |
          | category            | shop |
          | type                | bakery |
          | addresstype         | shop |
          | name                | Dorfbäckerei Herrmann |
          | display_name        | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |
          | boundingbox         | [47.0660392, 47.0661392, 9.5035565, 9.5036565] |
          | geojson+type        | Point |
          | geojson+coordinates | [9.5036065, 47.0660892] |

        Examples:
          | has_address | attributes    |
          | 1           | attributes    |
          | 0           | no attributes |

    Scenario: Reverse geojson - Tiger address
        When sending v1/reverse with format geojson
          | lat           | lon            |
          | 32.4752389363 | -86.4810198619 |
        Then a HTTP 200 is returned
        And the result is valid geojson with 1 result
        And all results contain
          | osm_type | osm_id    | category | type  | addresstype  | place_rank |
          | way      | 396009653 | place    | house | place        | 30         |

    Scenario: Reverse geojson - Interpolation address
        When sending v1/reverse with format geojson
          | lat       | lon        |
          | 47.118533 | 9.57056562 |
        Then a HTTP 200 is returned
        And the result is valid geojson with 1 result
        And all results contain
          | osm_type | osm_id | place_rank | category | type    | addresstype |
          | way      | 1      | 30         | place    | house   | place       |
        And all results contain
          | boundingbox!in_box |
          | 47.118494, 47.118596, 9.570495, 9.570597 |
        And all results contain
          | display_name |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

    Scenario: Reverse geojson - Line geometry output is supported
        When sending v1/reverse with format geojson
          | lat      | lon     | polygon_geojson |
          | 47.06597 | 9.50467 | 1               |
        Then a HTTP 200 is returned
        And the result is valid geojson with 1 result
        And all results contain
          | geojson+type |
          | LineString   |

    Scenario Outline: Reverse geojson - Only geojson polygons are supported
        When sending v1/reverse with format geojson
          | lat      | lon     | <param> |
          | 47.06597 | 9.50467 | 1       |
        Then a HTTP 200 is returned
        And the result is valid geojson with 1 result
        And all results contain
          | geojson+type |
          | Point |

        Examples:
          | param |
          | polygon_text |
          | polygon_svg  |
          | polygon_kml  |

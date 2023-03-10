@APIDB
Feature: Json output for Reverse API
    Testing correctness of json and jsonv2 output (API version v1).

    Scenario Outline: OSM result with and without addresses
        When sending v1/reverse at 47.066,9.504 with format json
          | addressdetails |
          | <has_address>  |
        Then result has <attributes> address
        When sending v1/reverse at 47.066,9.504 with format jsonv2
          | addressdetails |
          | <has_address>  |
        Then result has <attributes> address

        Examples:
          | has_address | attributes     |
          | 1           | attributes     |
          | 0           | not attributes |

    Scenario Outline: Siple OSM result
        When sending v1/reverse at 47.066,9.504 with format <format>
        Then result has attributes place_id
        And results contain
          | licence |
          | Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright |
        And results contain
          | osm_type | osm_id     |
          | node     | 6522627624 |
        And results contain
          | centroid             | boundingbox |
          | 9.5036065 47.0660892 | ['47.0660392', '47.0661392', '9.5035565', '9.5036565'] |
        And results contain
          | display_name |
          | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |
        And result has not attributes namedetails,extratags

        Examples:
          | format |
          | json   |
          | jsonv2 |

    Scenario: Extra attributes of jsonv2 result
        When sending v1/reverse at 47.066,9.504 with format jsonv2
        Then result has attributes importance
        Then results contain
          | category | type   | name                  | place_rank | addresstype |
          | shop     | bakery | Dorfbäckerei Herrmann | 30         | shop        |


    @Tiger
    Scenario: Tiger address
        When sending v1/reverse at 32.4752389363,-86.4810198619 with format jsonv2
        Then results contain
         | osm_type | osm_id    | category | type  | addresstype  |
         | way      | 396009653 | place    | house | place        |


    Scenario Outline: Interpolation address
        When sending v1/reverse at 47.118533,9.57056562 with format <format>
        Then results contain
          | osm_type | osm_id |
          | way      | 1      |
        And results contain
          | centroid                | boundingbox |
          | 9.57054676 47.118545392 | ['47.118495392', '47.118595392', '9.57049676', '9.57059676'] |
        And results contain
          | display_name |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

        Examples:
          | format |
          | json   |
          | jsonv2 |


    Scenario Outline: Output of geojson
       When sending v1/reverse at 47.06597,9.50467 with format <format>
          | param           | value |
          | polygon_geojson | 1     |
       Then results contain in field geojson
          | type       | coordinates |
          | LineString | [[9.5039353, 47.0657546], [9.5040437, 47.0657781], [9.5040808, 47.065787], [9.5054298, 47.0661407]] |

       Examples:
          | format |
          | json   |
          | jsonv2 |


    Scenario Outline: Output of WKT
       When sending v1/reverse at 47.06597,9.50467 with format <format>
          | param        | value |
          | polygon_text | 1     |
       Then results contain
          | geotext |
          | LINESTRING(9.5039353 47.0657546,9.5040437 47.0657781,9.5040808 47.065787,9.5054298 47.0661407) |

       Examples:
          | format |
          | json   |
          | jsonv2 |


    Scenario Outline: Output of SVG
       When sending v1/reverse at 47.06597,9.50467 with format <format>
          | param       | value |
          | polygon_svg | 1     |
       Then results contain
          | svg |
          | M 9.5039353 -47.0657546 L 9.5040437 -47.0657781 9.5040808 -47.065787 9.5054298 -47.0661407 |

       Examples:
          | format |
          | json   |
          | jsonv2 |


    Scenario Outline: Output of KML
       When sending v1/reverse at 47.06597,9.50467 with format <format>
          | param       | value |
          | polygon_kml | 1     |
       Then results contain
          | geokml |
          | ^<LineString><coordinates>9.5039\d*,47.0657\d* 9.5040\d*,47.0657\d* 9.5040\d*,47.065\d* 9.5054\d*,47.0661\d*</coordinates></LineString> |

       Examples:
          | format |
          | json   |
          | jsonv2 |

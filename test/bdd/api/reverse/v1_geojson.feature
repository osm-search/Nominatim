@APIDB
Feature: Geojson for Reverse API
    Testing correctness of geojson output (API version v1).

    Scenario Outline: Simple OSM result
        When sending v1/reverse at 47.066,9.504 with format geojson
          | addressdetails |
          | <has_address>  |
        Then result has attributes place_id, importance, __licence
        And result has <attributes> address
        And results contain
          | osm_type | osm_id     | place_rank | category | type    | addresstype |
          | node     | 6522627624 | 30         | shop     | bakery  | shop        |
        And results contain
          | name                  | display_name |
          | Dorfbäckerei Herrmann | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |
        And results contain
          | boundingbox |
          | [47.0660392, 47.0661392, 9.5035565, 9.5036565] |
        And results contain in field geojson
          | type  | coordinates |
          | Point | [9.5036065, 47.0660892] |

        Examples:
          | has_address | attributes     |
          | 1           | attributes     |
          | 0           | not attributes |


    @Tiger
    Scenario: Tiger address
        When sending v1/reverse at 32.4752389363,-86.4810198619 with format geojson
        Then results contain
         | osm_type | osm_id    | category | type  | addresstype  | place_rank |
         | way      | 396009653 | place    | house | place        | 30         |


    Scenario: Interpolation address
        When sending v1/reverse at 47.118533,9.57056562 with format geojson
        Then results contain
          | osm_type | osm_id | place_rank | category | type    | addresstype |
          | way      | 1      | 30         | place    | house   | place       |
        And results contain
          | boundingbox |
          | [47.118495392, 47.118595392, 9.57049676, 9.57059676] |
        And results contain
          | display_name |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |


    Scenario: Line geometry output is supported
        When sending v1/reverse at 47.06597,9.50467 with format geojson
          | param           | value |
          | polygon_geojson | 1     |
        Then results contain in field geojson
          | type       |
          | LineString |


    Scenario Outline: Only geojson polygons are supported
        When sending v1/reverse at 47.06597,9.50467 with format geojson
          | param   | value |
          | <param> | 1     |
        Then results contain in field geojson
          | type  |
          | Point |

        Examples:
          | param |
          | polygon_text |
          | polygon_svg  |
          | polygon_kml  |

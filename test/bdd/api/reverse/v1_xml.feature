@APIDB
Feature: XML output for Reverse API
    Testing correctness of xml output (API version v1).

    Scenario Outline: OSM result with and without addresses
        When sending v1/reverse at 47.066,9.504 with format xml
          | addressdetails |
          | <has_address>  |
        Then result has attributes place_id
        Then result has <attributes> address
        And results contain
          | osm_type | osm_id     | place_rank | address_rank |
          | node     | 6522627624 | 30         | 30           |
        And results contain
          | centroid             | boundingbox |
          | 9.5036065 47.0660892 | 47.0660392,47.0661392,9.5035565,9.5036565 |
        And results contain
          | ref                   | display_name |
          | Dorfbäckerei Herrmann | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |

        Examples:
          | has_address | attributes     |
          | 1           | attributes     |
          | 0           | not attributes |


    @Tiger
    Scenario: Tiger address
        When sending v1/reverse at 32.4752389363,-86.4810198619 with format xml
        Then results contain
         | osm_type | osm_id    | place_rank  | address_rank |
         | way      | 396009653 | 30          | 30           |
        And results contain
          | centroid                     | boundingbox |
          | -86.4808553258 32.4753580256 | ^32.475308025\d*,32.475408025\d*,-86.480905325\d*,-86.480805325\d* |
        And results contain
          | display_name |
          | 707, Upper Kingston Road, Upper Kingston, Prattville, Autauga County, 36067, United States |


    Scenario: Interpolation address
        When sending v1/reverse at 47.118533,9.57056562 with format xml
        Then results contain
          | osm_type | osm_id | place_rank | address_rank |
          | way      | 1      | 30         | 30           |
        And results contain
          | centroid                | boundingbox |
          | 9.57054676 47.118545392 | 47.118495392,47.118595392,9.57049676,9.57059676 |
        And results contain
          | display_name |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |


    Scenario: Output of geojson
       When sending v1/reverse at 47.06597,9.50467 with format xml
          | param           | value |
          | polygon_geojson | 1     |
       Then results contain
          | geojson |
          | {"type":"LineString","coordinates":[[9.5039353,47.0657546],[9.5040437,47.0657781],[9.5040808,47.065787],[9.5054298,47.0661407]]}  |


    Scenario: Output of WKT
       When sending v1/reverse at 47.06597,9.50467 with format xml
          | param        | value |
          | polygon_text | 1     |
       Then results contain
          | geotext |
          | LINESTRING(9.5039353 47.0657546,9.5040437 47.0657781,9.5040808 47.065787,9.5054298 47.0661407) |


    Scenario: Output of SVG
       When sending v1/reverse at 47.06597,9.50467 with format xml
          | param       | value |
          | polygon_svg | 1     |
       Then results contain
          | geosvg |
          | M 9.5039353 -47.0657546 L 9.5040437 -47.0657781 9.5040808 -47.065787 9.5054298 -47.0661407 |


    Scenario: Output of KML
       When sending v1/reverse at 47.06597,9.50467 with format xml
          | param       | value |
          | polygon_kml | 1     |
       Then results contain
          | geokml |
          | ^<geokml><LineString><coordinates>9.5039\d*,47.0657\d* 9.5040\d*,47.0657\d* 9.5040\d*,47.065\d* 9.5054\d*,47.0661\d*</coordinates></LineString></geokml> |

@APIDB
Feature: Geocodejson for Reverse API
    Testing correctness of geocodejson output (API version v1).

    Scenario Outline: Simple OSM result
        When sending v1/reverse at 47.066,9.504 with format geocodejson
          | addressdetails |
          | <has_address>  |
        Then result has attributes place_id, accuracy
        And result has <attributes> country,postcode,county,city,district,street,housenumber, admin
        Then results contain
          | osm_type | osm_id     | osm_key | osm_value | type  |
          | node     | 6522627624 | shop    | bakery    | house |
        And results contain
          | name                  | label |
          | Dorfbäckerei Herrmann | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |
        And results contain in field geojson
          | type  | coordinates             |
          | Point | [9.5036065, 47.0660892] |
        And results contain in field __geocoding
          | version | licence | attribution |
          | 0.1.0   | ODbL    | Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright |

        Examples:
          | has_address | attributes     |
          | 1           | attributes     |
          | 0           | not attributes |


    Scenario: City housenumber-level address with street
        When sending v1/reverse at 47.1068011,9.52810091 with format geocodejson
        Then results contain
          | housenumber | street    | postcode | city    | country |
          | 8           | Im Winkel | 9495     | Triesen | Liechtenstein |
         And results contain in field admin
          | level6   | level8  |
          | Oberland | Triesen |


    Scenario: Town street-level address with street
        When sending v1/reverse at 47.066,9.504 with format geocodejson
          | zoom |
          | 16 |
        Then results contain
          | name    | city    | postcode | country |
          | Gnetsch | Balzers | 9496     | Liechtenstein |


    Scenario: Poi street-level address with footway
        When sending v1/reverse at 47.06515,9.50083 with format geocodejson
        Then results contain
          | street  | city    | postcode | country |
          | Burgweg | Balzers | 9496     | Liechtenstein |


    Scenario: City address with suburb
        When sending v1/reverse at 47.146861,9.511771 with format geocodejson
        Then results contain
          | housenumber | street   | district | city  | postcode | country |
          | 5           | Lochgass | Ebenholz | Vaduz | 9490     | Liechtenstein |


    @Tiger
    Scenario: Tiger address
        When sending v1/reverse at 32.4752389363,-86.4810198619 with format geocodejson
        Then results contain
         | osm_type | osm_id    | osm_key | osm_value | type  |
         | way      | 396009653 | place   | house     | house |
        And results contain
         | housenumber | street              | city       | county         | postcode | country       |
         | 707         | Upper Kingston Road | Prattville | Autauga County | 36067    | United States |


    Scenario: Interpolation address
        When sending v1/reverse at 47.118533,9.57056562 with format geocodejson
        Then results contain
          | osm_type | osm_id | osm_key | osm_value | type  |
          | way      | 1      | place   | house     | house |
        And results contain
          | label |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |
        And result has not attributes name


    Scenario: Line geometry output is supported
        When sending v1/reverse at 47.06597,9.50467 with format geocodejson
          | param           | value |
          | polygon_geojson | 1     |
        Then results contain in field geojson
          | type       |
          | LineString |


    Scenario Outline: Only geojson polygons are supported
        When sending v1/reverse at 47.06597,9.50467 with format geocodejson
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

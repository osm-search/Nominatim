@APIDB
Feature: v1/reverse Parameter Tests
    Tests for parameter inputs for the v1 reverse endpoint.
    This file contains mostly bad parameter input. Valid parameters
    are tested in the format tests.

    Scenario: Bad format
        When sending v1/reverse at 47.14122383,9.52169581334 with format sdf
        Then a HTTP 400 is returned

    Scenario: Missing lon parameter
        When sending v1/reverse at 52.52,
        Then a HTTP 400 is returned


    Scenario: Missing lat parameter
        When sending v1/reverse at ,52.52
        Then a HTTP 400 is returned

    @v1-api-php-only
    Scenario: Missing osm_id parameter
        When sending v1/reverse at ,
          | osm_type |
          | N |
        Then a HTTP 400 is returned

    @v1-api-php-only
    Scenario: Missing osm_type parameter
        When sending v1/reverse at ,
          | osm_id |
          | 3498564 |
        Then a HTTP 400 is returned


    Scenario Outline: Bad format for lat or lon
        When sending v1/reverse at ,
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
          | Nan      | 8.448  |
          | 48.966   | Nan    |
          | Inf      | 5.6    |
          | 5.6      | -Inf   |
          | <script></script> | 3.4 |
          | 3.4 | <script></script> |
          | -45.3    | ;      |
          | gkjd     | 50     |


    Scenario: Non-numerical zoom levels return an error
        When sending v1/reverse at 47.14122383,9.52169581334
          | zoom |
          | adfe |
        Then a HTTP 400 is returned


    Scenario Outline: Truthy values for boolean parameters
        When sending v1/reverse at 47.14122383,9.52169581334
          | addressdetails |
          | <value> |
        Then exactly 1 result is returned
        And result has attributes address

        When sending v1/reverse at 47.14122383,9.52169581334
          | extratags |
          | <value> |
        Then exactly 1 result is returned
        And result has attributes extratags

        When sending v1/reverse at 47.14122383,9.52169581334
          | namedetails |
          | <value> |
        Then exactly 1 result is returned
        And result has attributes namedetails

        When sending v1/reverse at 47.14122383,9.52169581334
          | polygon_geojson |
          | <value> |
        Then exactly 1 result is returned
        And result has attributes geojson

        When sending v1/reverse at 47.14122383,9.52169581334
          | polygon_kml |
          | <value> |
        Then exactly 1 result is returned
        And result has attributes geokml

        When sending v1/reverse at 47.14122383,9.52169581334
          | polygon_svg |
          | <value> |
        Then exactly 1 result is returned
        And result has attributes svg

        When sending v1/reverse at 47.14122383,9.52169581334
          | polygon_text |
          | <value> |
        Then exactly 1 result is returned
        And result has attributes geotext

        Examples:
          | value |
          | yes   |
          | no    |
          | -1    |
          | 100   |
          | false |
          | 00    |


    Scenario: Only one geometry can be requested
        When sending v1/reverse at 47.165989816710066,9.515774846076965
          | polygon_text | polygon_svg |
          | 1            | 1           |
        Then a HTTP 400 is returned


    Scenario Outline: Wrapping of legal jsonp requests
        When sending v1/reverse at 67.3245,0.456 with format <format>
          | json_callback |
          | foo |
        Then the result is valid <outformat>

        Examples:
          | format      | outformat   |
          | json        | json        |
          | jsonv2      | json        |
          | geojson     | geojson     |
          | geocodejson | geocodejson |


    Scenario Outline: Illegal jsonp are not allowed
        When sending v1/reverse at 47.165989816710066,9.515774846076965
          | param        | value |
          |json_callback | <data> |
        Then a HTTP 400 is returned

        Examples:
          | data |
          | 1asd |
          | bar(foo) |
          | XXX['bad'] |
          | foo; evil |


    @v1-api-python-only
    Scenario Outline: Reverse debug mode produces valid HTML
        When sending v1/reverse at , with format debug
          | lat   | lon   |
          | <lat> | <lon> |
        Then the result is valid html

        Examples:
          | lat      | lon     |
          | 0.0      | 0.0     |
          | 47.06645 | 9.56601 |
          | 47.14081 | 9.52267 |


    Scenario Outline: Full address display for city housenumber-level address with street
        When sending v1/reverse at 47.1068011,9.52810091 with format <format>
        Then address of result 0 is
          | type           | value     |
          | house_number   | 8         |
          | road           | Im Winkel |
          | neighbourhood  | Oberdorf  |
          | village        | Triesen   |
          | ISO3166-2-lvl8 | LI-09     |
          | county         | Oberland  |
          | postcode       | 9495      |
          | country        | Liechtenstein |
          | country_code   | li        |

        Examples:
          | format  |
          | json    |
          | jsonv2  |
          | geojson |
          | xml     |


    Scenario Outline: Results with name details
        When sending v1/reverse at 47.14052,9.52202 with format <format>
          | zoom | namedetails |
          | 14   | 1           |
        Then results contain in field namedetails
          | name     |
          | Ebenholz |

        Examples:
          | format  |
          | json    |
          | jsonv2  |
          | xml     |
          | geojson |


    Scenario Outline: Results with extratags
        When sending v1/reverse at 47.14052,9.52202 with format <format>
          | zoom | extratags |
          | 14   | 1         |
        Then results contain in field extratags
          | wikidata |
          | Q4529531 |

        Examples:
          | format |
          | json   |
          | jsonv2 |
          | xml    |
          | geojson |



Feature: v1/reverse Parameter Tests
    Tests for parameter inputs for the v1 reverse endpoint.
    This file contains mostly bad parameter input. Valid parameters
    are tested in the format tests.

    Scenario: Bad format
        When sending v1/reverse
          | lat         | lon           | format |
          | 47.14122383 | 9.52169581334 | sdf |
        Then a HTTP 400 is returned

    Scenario: Missing lon parameter
        When sending v1/reverse
          | lat   |
          | 52.52 |
        Then a HTTP 400 is returned

    Scenario: Missing lat parameter
        When sending v1/reverse
          | lon |
          | 52.52 |
        Then a HTTP 400 is returned

    Scenario Outline: Bad format for lat or lon
        When sending v1/reverse
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
        When sending v1/reverse
          | lat         | lon           | zoom |
          | 47.14122383 | 9.52169581334 | adfe |
        Then a HTTP 400 is returned

    Scenario Outline: Truthy values for boolean parameters
        When sending v1/reverse
          | lat         | lon           | addressdetails |
          | 47.14122383 | 9.52169581334 | <value> |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result has attributes address

        When sending v1/reverse
          | lat         | lon           | extratags |
          | 47.14122383 | 9.52169581334 | <value> |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result has attributes extratags

        When sending v1/reverse
          | lat         | lon           | namedetails |
          | 47.14122383 | 9.52169581334 | <value> |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result has attributes namedetails

        Examples:
          | value |
          | yes   |
          | no    |
          | -1    |
          | 100   |
          | false |
          | 00    |

    Scenario: Only one geometry can be requested
        When sending v1/reverse
          | lat         | lon           | polygon_text | polygon_svg |
          | 47.14122383 | 9.52169581334 | 1            | 1           |
        Then a HTTP 400 is returned

    Scenario Outline: Illegal jsonp are not allowed
        When sending v1/reverse with format json
          | lat         | lon           | json_callback |
          | 47.14122383 | 9.52169581334 | <data> |
        Then a HTTP 400 is returned

        Examples:
          | data |
          | 1asd |
          | bar(foo) |
          | XXX['bad'] |
          | foo; evil |

    Scenario Outline: Reverse debug mode produces valid HTML
        When sending v1/reverse
          | lat   | lon   | debug |
          | <lat> | <lon> | 1 |
        Then a HTTP 200 is returned
        And the result is valid html

        Examples:
          | lat      | lon     |
          | 0.0      | 0.0     |
          | 47.06645 | 9.56601 |
          | 47.14081 | 9.52267 |

    Scenario Outline: Full address display for city housenumber-level address with street
        When sending v1/reverse with format <format>
          | lat        | lon        |
          | 47.1068011 | 9.52810091 |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And the result contains in field address
          | param          | value     |
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
          | format  | outformat |
          | json    | json |
          | jsonv2  | json |
          | xml     | xml |

    Scenario Outline: Results with name details
        When sending v1/reverse with format <format>
          | lat      | lon     | zoom | namedetails |
          | 47.14052 | 9.52202 | 14   | 1           |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And the result contains in field namedetails
          | name     |
          | Ebenholz |

        Examples:
          | format  | outformat |
          | json    | json |
          | jsonv2  | json |
          | xml     | xml |

    Scenario Outline: Results with extratags
        When sending v1/reverse with format <format>
          | lat      | lon     | zoom | extratags |
          | 47.14052 | 9.52202 | 14   | 1         |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And the result contains in field extratags
          | wikidata |
          | Q4529531 |

        Examples:
          | format | outformat |
          | json   | json |
          | jsonv2 | json |
          | xml    | xml |

    Scenario Outline: Reverse with entrances
        When sending v1/reverse with format <format>
          | lat               | lon              | entrances | zoom |
          | 47.24942041089678 | 9.52854573737568 | 1         | 18   |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And the result contains array field entrances where element 0 contains
          | osm_id     | type | lat        | lon       |
          | 6580031131 | yes  | 47.2489382 | 9.5284033 |

        Examples:
          | format | outformat |
          | json   | json |
          | jsonv2 | json |

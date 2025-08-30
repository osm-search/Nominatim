Feature: Object details
    Testing different parameter options for details API.

    Scenario: Basic details
        When sending v1/details
          | osmtype | osmid |
          | W       | 297699560 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes geometry
        And the result has no attributes keywords,address,linked_places,parentof
        And the result contains
            | geometry+type  |
            | Point |

    Scenario: Basic details with pretty printing
        When sending v1/details
          | osmtype | osmid     | pretty |
          | W       | 297699560 | 1      |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes geometry
        And the result has no attributes keywords,address,linked_places,parentof

    Scenario: Details with addressdetails
        When sending v1/details
          | osmtype | osmid     | addressdetails |
          | W       | 297699560 | 1              |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes address

    Scenario: Details with entrances
        When sending v1/details
          | osmtype | osmid     | entrances |
          | W       | 429210603 | 1         |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains array field entrances where element 0 contains
          | osm_id     | type | lat        | lon       |
          | 6580031131 | yes  | 47.2489382 | 9.5284033 |

    Scenario: Details with linkedplaces
        When sending v1/details
          | osmtype | osmid  | linkedplaces |
          | R       | 123924 | 1            |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes linked_places

    Scenario: Details with hierarchy
        When sending v1/details
          | osmtype | osmid     | hierarchy |
          | W       | 297699560 | 1         |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes hierarchy

    Scenario: Details with grouped hierarchy
        When sending v1/details
          | osmtype | osmid     | hierarchy | group_hierarchy |
          | W       | 297699560 | 1         | 1               |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes hierarchy

    Scenario Outline: Details with keywords
        When sending v1/details
            | osmtype | osmid | keywords |
            | <type>  | <id>  | 1 |
        Then a HTTP 200 is returned
        Then the result is valid json
        And the result has attributes keywords

    Examples:
      | type | id |
      | W    | 297699560 |
      | W    | 243055645 |
      | W    | 243055716 |
      | W    | 43327921  |

    # ticket #1343
    Scenario: Details of a country with keywords
        When sending v1/details
            | osmtype | osmid   | keywords |
            | R       | 1155955 | 1 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes keywords

    Scenario Outline: Details with full geometry
        When sending v1/details
            | osmtype | osmid | polygon_geojson |
            | <type>  | <id>  | 1 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result has attributes geometry
        And the result contains
            | geometry+type |
            | <geometry> |

    Examples:
            | type | id        | geometry   |
            | W    | 297699560 | LineString |
            | W    | 243055645 | Polygon    |
            | W    | 243055716 | Polygon    |
            | W    | 43327921  | LineString |



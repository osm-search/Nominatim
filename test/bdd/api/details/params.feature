@APIDB
Feature: Object details
    Testing different parameter options for details API.

    @SQLITE
    Scenario: JSON Details
        When sending json details query for W297699560
        Then the result is valid json
        And result has attributes geometry
        And result has not attributes keywords,address,linked_places,parentof
        And results contain in field geometry
            | type  |
            | Point |

    @SQLITE
    Scenario: JSON Details with pretty printing
        When sending json details query for W297699560
            | pretty |
            | 1      |
        Then the result is valid json
        And result has attributes geometry
        And result has not attributes keywords,address,linked_places,parentof

    @SQLITE
     Scenario: JSON Details with addressdetails
        When sending json details query for W297699560
            | addressdetails |
            | 1 |
        Then the result is valid json
        And result has attributes address

    @SQLITE
    Scenario: JSON Details with linkedplaces
        When sending json details query for R123924
            | linkedplaces |
            | 1 |
        Then the result is valid json
        And result has attributes linked_places

    @SQLITE
    Scenario: JSON Details with hierarchy
        When sending json details query for W297699560
            | hierarchy |
            | 1 |
        Then the result is valid json
        And result has attributes hierarchy

    @SQLITE
    Scenario: JSON Details with grouped hierarchy
        When sending json details query for W297699560
            | hierarchy | group_hierarchy |
            | 1         | 1 |
        Then the result is valid json
        And result has attributes hierarchy

     Scenario Outline: JSON Details with keywords
        When sending json details query for <osmid>
            | keywords |
            | 1 |
        Then the result is valid json
        And result has attributes keywords

    Examples:
            | osmid |
            | W297699560 |
            | W243055645 |
            | W243055716 |
            | W43327921  |

    # ticket #1343
    Scenario: Details of a country with keywords
        When sending details query for R1155955
            | keywords |
            | 1 |
        Then the result is valid json
        And result has attributes keywords

    @SQLITE
    Scenario Outline: JSON details with full geometry
        When sending json details query for <osmid>
            | polygon_geojson |
            | 1 |
        Then the result is valid json
        And result has attributes geometry
        And results contain in field geometry
            | type       |
            | <geometry> |

    Examples:
            | osmid      | geometry   |
            | W297699560 | LineString |
            | W243055645 | Polygon    |
            | W243055716 | Polygon    |
            | W43327921  | LineString |



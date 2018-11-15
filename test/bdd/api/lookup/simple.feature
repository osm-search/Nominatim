@APIDB
Feature: Places by osm_type and osm_id Tests
    Simple tests for response format.

    Scenario Outline: address lookup for existing node, way, relation
        When sending <format> lookup query for N3284625766,W6065798,,R123924,X99,N0
        Then the result is valid <format>
        And exactly 3 results are returned

    Examples:
        | format  |
        | xml     |
        | json    |
        | geojson |

    Scenario: address lookup for non-existing or invalid node, way, relation
        When sending xml lookup query for X99,,N0,nN158845944,ABC,,W9
        Then exactly 0 results are returned

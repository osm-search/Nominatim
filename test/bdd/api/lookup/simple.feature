@APIDB
Feature: Places by osm_type and osm_id Tests
    Simple tests for response format.

    Scenario Outline: address lookup for existing node, way, relation
        When sending <format> lookup query for N3284625766,W6065798,,R123924,X99,N0
        Then the result is valid <outformat>
        And exactly 3 results are returned

    Examples:
        | format      | outformat   |
        | xml         | xml         |
        | json        | json        |
        | jsonv2      | json        |
        | geojson     | geojson     |
        | geocodejson | geocodejson |

    Scenario: address lookup for non-existing or invalid node, way, relation
        When sending xml lookup query for X99,,N0,nN158845944,ABC,,W9
        Then exactly 0 results are returned

    Scenario Outline: Boundingbox is returned
        When sending <format> lookup query for N3284625766,W6065798
        Then exactly 2 results are returned
        And result 0 has bounding box in -32.812,-32.811,-56.509,-56.508
        And result 1 has bounding box in 47.14,47.15,9.51,9.53

    Examples:
      | format |
      | json |
      | jsonv2 |
      | geojson |
      | xml |

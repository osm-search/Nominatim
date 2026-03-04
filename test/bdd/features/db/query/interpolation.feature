Feature: Query of address interpolations
    Tests that interpolated addresses can be queried correctly

    Background:
        Given the grid
          | 1  |  | 2  |  | 3  |
          | 10 |  | 12 |  | 13 |
          | 7  |  | 8  |  | 9  |

    Scenario: Find interpolations with single number
        Given the places
          | osm | class   | type    | name    | geometry |
          | W10 | highway | primary | Nickway | 10,12,13 |
        And the interpolations
          | osm | type | geometry | nodes |
          | W1  | odd  | 1,3      | 1,3   |
        And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 1       | 1        |
          | N3  | place | house | 5       | 3        |
        When importing
        When reverse geocoding at node 2
        Then the result contains
          | display_name |
          | 3, Nickway   |
        When geocoding "Nickway 3"
        Then all results contain
          | object | display_name |
          | W1     | 3, Nickway   |


    Scenario: Find interpolations with multiple numbers
        Given the places
          | osm | class   | type    | name    | geometry |
          | W10 | highway | primary | Nickway | 10,12,13 |
        And the interpolations
          | osm | type | geometry | nodes |
          | W1  | even | 1,3      | 1,3   |
        And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 1        |
          | N3  | place | house | 18      | 3        |
        When importing
        When reverse geocoding at node 2
        Then the result contains
          | display_name | centroid!wkt |
          | 10, Nickway  | 2 |
        When geocoding "Nickway 10"
        Then all results contain
          | object | display_name  | centroid!wkt |
          | W1     | 10, Nickway   | 2 |


    Scenario: Interpolations are found according to their type
        Given the grid
         | 10  |  | 11  |
         | 100 |  | 101 |
         | 20  |  | 21  |
        And the places
         | osm  | class   | type        | name    | geometry |
         | W100 | highway | residential | Ringstr | 100, 101 |
        And the interpolations
         | osm | type | geometry | nodes |
         | W10 | even | 10, 11   | 10, 11 |
         | W20 | odd  | 20, 21   | 20, 21 |
        And the places
         | osm | class | type  | housenr | geometry |
         | N10 | place | house | 10      | 10 |
         | N11 | place | house | 20      | 11 |
         | N20 | place | house | 11      | 20 |
         | N21 | place | house | 21      | 21 |
        When importing
        When geocoding "Ringstr 12"
        Then the result set contains
         | object |
         | W10 |
        When geocoding "Ringstr 13"
        Then the result set contains
         | object |
         | W20 |

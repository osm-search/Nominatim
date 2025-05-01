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
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | odd                | 1,3      |
        And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 1       | 1        |
          | N3  | place | house | 5       | 3        |
        And the ways
          | id | nodes |
          | 1  | 1,3   |
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
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3      |
        And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 1        |
          | N3  | place | house | 18      | 3        |
        And the ways
          | id | nodes |
          | 1  | 1,3   |
        When importing
        When reverse geocoding at node 2
        Then the result contains
          | display_name | centroid!wkt |
          | 10, Nickway  | 2 |
        When geocoding "Nickway 10"
        Then all results contain
          | object | display_name  | centroid!wkt |
          | W1     | 10, Nickway   | 2 |

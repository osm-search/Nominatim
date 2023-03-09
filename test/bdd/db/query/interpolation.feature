@DB
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
        When sending jsonv2 reverse point 2
        Then results contain
          | ID | display_name |
          | 0  | 3, Nickway   |
        When sending search query "Nickway 3"
        Then results contain
          | osm | display_name |
          | W1  | 3, Nickway   |


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
        When sending jsonv2 reverse point 2
        Then results contain
          | ID | display_name | centroid |
          | 0  | 10, Nickway  | 2 |
        When sending search query "Nickway 10"
        Then results contain
          | osm | display_name  | centroid |
          | W1  | 10, Nickway   | 2 |

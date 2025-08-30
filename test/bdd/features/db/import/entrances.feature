Feature: Entrance nodes are recorded
    Test that imported entrance nodes are saved

    Scenario: A building with two entrances
        Given the grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type  | geometry    | extratags           |
          | W1  | building | yes   | (1,2,3,4,1) |                     |
          | N1  | entrance | main  | 1           | 'wheelchair': 'yes' |
          | N2  | entrance | yes   | 3           |                     |
        And the ways
          | id | nodes     |
          | 1  | 1,2,3,4,1 |
        When importing
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        Then placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags             |
         | 1        | 1      | main | 1            | {'wheelchair': 'yes'} |
         | 1        | 2      | yes  | 3            | {}                    |

Feature: Entrance nodes are recorded
    Test that updated entrance nodes are saved

    Scenario: A building with a newly tagged entrance
        Given the grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm  | class    | type  | geometry    |
          | W1   | building | yes   | (1,2,3,4,1) |
        And the ways
          | id | nodes         |
          | 1  | 1, 2, 3, 4, 1 |
        When importing
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        Then placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |
        When updating places
          | osm | class    | type  | geometry    |
          | N1  | entrance | main  | 1           |
          | W1  | building | yes   | (1,2,3,4,1) |
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        Then placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |
         | 1        | 1      | main | 1            | -         |

    Scenario: A building with a updated entrance node
        Given the grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type  | geometry    |
          | N1  | barrier  | gate  | 1           |
          | W1  | building | yes   | (1,2,3,4,1) |
        And the ways
          | id | nodes         |
          | 1  | 1, 2, 3, 4, 1 |
        When importing
        Then placex contains exactly
         | object | place_id |
         | N1     | 1        |
         | W1     | 2        |
        Then placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |
        When updating places
          | osm | class    | type  | geometry    |
          | N1  | entrance | main  | 1           |
          | W1  | building | yes   | (1,2,3,4,1) |
        Then placex contains exactly
         | object | place_id |
         | N1     | 1        |
         | W1     | 2        |
        And placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |
         | 2        | 1      | main | 1            | -         |

    Scenario: A building with a removed entrance
        Given the grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type  | geometry    |
          | N1  | entrance | main  | 1           |
          | W1  | building | yes   | (1,2,3,4,1) |
        And the ways
          | id | nodes         |
          | 1  | 1, 2, 3, 4, 1 |
        When importing
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        And placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |
         | 1        | 1      | main | 1            | -         |
        When marking for delete N1
        And updating places
          | osm | class    | type  | geometry  |
          | W1  | building | yes   | (2,3,4,2) |
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        And placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |

    Scenario: A building with a removed and remaining entrance
        Given the grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type  | geometry    |
          | N1  | entrance | main  | 1           |
          | N3  | entrance | yes   | 3           |
          | W1  | building | yes   | (1,2,3,4,1) |
        And the ways
          | id | nodes         |
          | 1  | 1, 2, 3, 4, 1 |
        When importing
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        And placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |
         | 1        | 1      | main | 1            | -         |
         | 1        | 3      | yes  | 3            | -         |
        When marking for delete N1
        And updating places
          | osm | class    | type  | geometry  |
          | W1  | building | yes   | (2,3,4,2) |
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        And placex_entrance contains exactly
         | place_id | osm_id | type | location!wkt | extratags |
         | 1        | 3      | yes  | 3            | -         |

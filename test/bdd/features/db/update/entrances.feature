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
        Then place_entrance contains exactly
         | place_id | entrances |
        When updating places
          | osm | class    | type  | geometry    |
          | N1  | entrance | main  | 1           |
          | W1  | building | yes   | (1,2,3,4,1) |
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        And place_entrance contains exactly
         | place_id | entrances |
         | 1        | [{'lat': 0, 'lon': 0, 'type': 'main', 'osm_id': 1, 'extratags': None}] |

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
        Then place_entrance contains exactly
         | place_id | entrances |
        When updating places
          | osm | class    | type  | geometry    |
          | N1  | entrance | main  | 1           |
          | W1  | building | yes   | (1,2,3,4,1) |
        Then placex contains exactly
         | object | place_id |
         | N1     | 1        |
         | W1     | 2        |
        And place_entrance contains exactly
         | place_id | entrances |
         | 2        | [{'lat': 0, 'lon': 0, 'type': 'main', 'osm_id': 1, 'extratags': None}] |

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
        And place_entrance contains exactly
         | place_id | entrances |
         | 1        | [{'lat': 0, 'lon': 0, 'type': 'main', 'osm_id': 1, 'extratags': None}] |
        When marking for delete N1
        And updating places
          | osm | class    | type  | geometry  |
          | W1  | building | yes   | (2,3,4,2) |
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        And place_entrance contains exactly
         | place_id | entrances |

Feature: Entrance nodes are recorded
    Test that imported entrance nodes are saved

    Scenario: A building with two entrances
        Given the grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm  | class    | type  | geometry    | extratags           |
          | W1   | building | yes   | (1,2,3,4,1) |                     |
          | N10  | entrance | main  | 1           | 'wheelchair': 'yes' |
          | N20  | entrance | yes   | 3           |                     |
        And the ways
          | id | nodes       |
          | 1  | 10,20,30,40 |
        When importing
        Then placex contains exactly
         | object | place_id |
         | W1     | 1        |
        Then place_entrance contains exactly
         | place_id | entrances |
         | 1        | [{'lat': 0, 'lon': 0, 'type': 'main', 'osm_id': 10, 'extratags': {'wheelchair': 'yes'}}, {'lat': 1e-05, 'lon': 1e-05, 'type': 'yes', 'osm_id': 20, 'extratags': {}}] |

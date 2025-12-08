Feature: Reverse searches
    Test results of reverse queries

    Scenario: POI in POI area
        Given the 0.0001 grid with origin 1,1
          | 1 |   |  |  |  |  |  |  | 2 |
          |   | 9 |  |  |  |  |  |  |   |
          | 4 |   |  |  |  |  |  |  | 3 |
        And the places
          | osm | class   | type       | geometry    |
          | W1  | aeroway | terminal   | (1,2,3,4,1) |
          | N9  | amenity | restaurant | 9           |
        When importing
        And reverse geocoding 1.0001,1.0001
        Then the result contains
         | object |
         | N9  |
        When reverse geocoding 1.0003,1.0001
        Then the result contains
         | object |
         | W1  |


    Scenario: Find closest housenumber for street matches
        Given the 0.0001 grid with origin 1,1
          |    | 1 |   |    |
          |    |   | 2 |    |
          | 10 |   |   | 11 |
        And the places
          | osm | class   | type     | name        | geometry |
          | W1  | highway | service  | Goose Drive | 10,11    |
          | N2  | tourism | art_work | Beauty      | 2        |
        And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 23      | 1        |
        When importing
        When reverse geocoding 1.0002,1.0002
        Then the result contains
          | object |
          | N1 |

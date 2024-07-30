@DB
Feature: Reverse searches
    Test results of reverse queries

    @v1-api-python-only
    Scenario: POI in POI area
        Given the 0.0001 grid with origin 1,1
          | 1 |   |  |  |  |  |  |  | 2 |
          |   | 9 |  |  |  |  |  |  |   |
          | 4 |   |  |  |  |  |  |  | 3 |
        And the places
          | osm | class   | type       | geometry    |
          | W1  | aeroway | terminal   | (1,2,3,4,1) |
          | N1  | amenity | restaurant | 9           |
        When importing
        And sending v1/reverse at 1.0001,1.0001
        Then results contain
         | osm |
         | N1  |
        When sending v1/reverse at 1.0003,1.0001
        Then results contain
         | osm |
         | W1  |

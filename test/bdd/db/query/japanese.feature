@DB
Feature: Searches in Japan
    Test specifically for searches of Japanese addresses and in Japanese language.
    @fail-legacy
    Scenario: A block house-number is parented to the neighbourhood
        Given the grid with origin JP
          | 1 |   |   |   | 2 |
          |   | 3 |   |   |   |
          |   |   | 9 |   |   |
          |   |   |   | 6 |   |
        And the places
          | osm | class   | type        | name       | geometry |
          | W1  | highway | residential | 雉子橋通り | 1,2      |
        And the places
          | osm | class   | type       | housenr | addr+block_number | addr+neighbourhood | geometry |
          | N3  | amenity | restaurant | 2       | 6                 | 2丁目              | 3        |
        And the places
          | osm | class | type          | name  | geometry |
          | N9  | place | neighbourhood | 2丁目 | 9        |
        And the places
          | osm | class | type    | name | geometry |
          | N6  | place | quarter | 加瀬 | 6        |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N3     | N9              |
        When sending search query "2丁目 6-2"
        Then results contain
          | osm |
          | N3  |

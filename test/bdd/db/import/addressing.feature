@DB
Feature: Address computation
    Tests for filling of place_addressline

    # github #121
    Scenario: Roads crossing boundaries should contain both states
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   | 7 |   | 8 |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 7, 8     |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
            | W1     | W11     | 10                  |

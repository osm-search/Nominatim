@DB
Feature: Address computation
    Tests for filling of place_addressline

    # github #121
    Scenario: Roads crossing boundaries should contain both states
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   | 7 |   |   | 8 |   |
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


    Scenario: Roads following a boundary should contain both states
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   |   | 8 | 7 |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 2, 7, 8  |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
            | W1     | W11     | 10                  |

    Scenario: Roads should not contain boundaries they touch in a end point
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   | 7 |   | 8 |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 7, 8     |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 8, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 8, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
        Then place_addressline doesn't contain
            | object | address |
            | W1     | W11     |

    Scenario: Roads should not contain boundaries they touch in a end point
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   | 7 |   | 8 |   |   |
            | 4 |   | 9 | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 7, 8, 9     |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 8, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 8, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
        Then place_addressline doesn't contain
            | object | address |
            | W1     | W11     |

    Scenario: Locality points should contain all boundaries they touch
        Given the 0.001 grid
            | 1 |   |   | 2 |   | 3 |
            |   |   |   | 8 |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class | type     | geometry |
            | N1  | place | locality | 8        |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 8, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 8, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | N1     | W10     | 10                  |
            | N1     | W11     | 10                  |

    Scenario: Areas should not contain boundaries they touch
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   |   |   |   |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class    | type           | geometry      |
            | W1  | landuse  | industrial     | (1, 2, 5, 4, 1) |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (2, 3, 6, 5, 2) |
        When importing
        Then place_addressline doesn't contain
            | object | address |
            | W1     | W10     |

    Scenario: buildings with only addr:postcodes do not appear in the address of a way
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
            | R4  | boundary | administrative | 10    | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        And the places
            | osm | class    | type        | addr+postcode | geometry |
            | W22 | place    | postcode    | 445023        | :building:w2N |
        When importing
        Then place_addressline doesn't contain
            | object | address  |
            | W93    | W22      |

    Scenario: postcode boundaries do appear in the address of a way
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
        And the places
            | osm | class    | type      | addr+postcode | geometry |
            | R4  | place    | postcode  | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        And the places
            | osm | class    | type        | addr+postcode | geometry |
            | W22 | place    | postcode    | 445023        | :building:w2N |
        When importing
        Then place_addressline contains
            | object | address |
            | W93    | R4      |

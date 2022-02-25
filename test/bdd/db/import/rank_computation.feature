@DB
Feature: Rank assignment
    Tests for assignment of search and address ranks.

    Scenario: Ranks for place nodes are assigned according to their type
        Given the named places
          | osm  | class     | type      | geometry |
          | N1   | foo       | bar       | 0 0 |
          | N11  | place     | Continent | 0 0 |
          | N12  | place     | continent | 0 0 |
          | N13  | place     | sea       | 0 0 |
          | N14  | place     | country   | 0 0 |
          | N15  | place     | state     | 0 0 |
          | N16  | place     | region    | 0 0 |
          | N17  | place     | county    | 0 0 |
          | N18  | place     | city      | 0 0 |
          | N19  | place     | island    | 0 0 |
          | N36  | place     | house     | 0 0 |
        And the named places
          | osm  | class     | type      | extra+capital | geometry |
          | N101 | place     | city      | yes           | 0 0 |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | N1     | 30          | 30 |
          | N11    | 22          | 0 |
          | N12    | 2           | 0 |
          | N13    | 2           | 0 |
          | N14    | 4           | 0 |
          | N15    | 8           | 0 |
          | N16    | 18          | 0 |
          | N17    | 12          | 12 |
          | N18    | 16          | 16 |
          | N19    | 17          | 0 |
          | N101   | 15          | 16 |
          | N36    | 30          | 30 |

    Scenario: Ranks for boundaries are assigned according to admin level
        Given the named places
          | osm | class    | type           | admin | geometry |
          | R20 | boundary | administrative | 2     | (1 1, 2 2, 1 2, 1 1) |
          | R21 | boundary | administrative | 32    | (3 3, 4 4, 3 4, 3 3) |
          | R22 | boundary | administrative | 6     | (0 0, 1 0, 0 1, 0 0) |
          | R23 | boundary | administrative | 10    | (0 0, 1 1, 1 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R20    | 4           | 4 |
          | R21    | 25          | 0 |
          | R22    | 12          | 12 |
          | R23    | 20          | 20 |

    Scenario: Ranks for addressable boundaries with place assignment go with place address ranks if available
        Given the named places
          | osm | class    | type           | admin | extra+place | geometry |
          | R20 | boundary | administrative | 3     | state       | (1 1, 2 2, 1 2, 1 1) |
          | R21 | boundary | administrative | 32    | suburb      | (3 3, 4 4, 3 4, 3 3) |
          | R22 | boundary | administrative | 6     | town        | (0 0, 1 0, 0 1, 0 0) |
          | R23 | boundary | administrative | 10    | village     | (0 0, 1 1, 1 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R20    | 6           | 6  |
          | R21    | 25          | 0  |
          | R22    | 12          | 16 |
          | R23    | 20          | 16 |

    Scenario: Place address ranks cannot overtake a parent address rank
        Given the named places
          | osm | class    | type           | admin | extra+place  | geometry |
          | R20 | boundary | administrative | 8     | town         | (0 0, 0 2, 2 2, 2 0, 0 0) |
          | R21 | boundary | administrative | 9     | municipality | (0 0, 0 1, 1 1, 1 0, 0 0) |
          | R22 | boundary | administrative | 9     | suburb       | (0 0, 0 1, 1 1, 1 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R20    | 16          | 16 |
          | R21    | 18          | 18 |
          | R22    | 18          | 20 |
        Then place_addressline contains
            | object | address | cached_rank_address |
            | R21    | R20     | 16                  |
            | R22    | R20     | 16                  |

    Scenario: Admin levels cannot overtake each other due to place address ranks
        Given the named places
          | osm | class    | type           | admin | extra+place  | geometry |
          | R20 | boundary | administrative | 6     | town         | (0 0, 0 2, 2 2, 2 0, 0 0) |
          | R21 | boundary | administrative | 8     |              | (0 0, 0 1, 1 1, 1 0, 0 0) |
          | R22 | boundary | administrative | 8     | suburb       | (0 0, 0 1, 1 1, 1 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R20    | 12          | 16 |
          | R21    | 16          | 18 |
          | R22    | 16          | 20 |
        Then place_addressline contains
            | object | address | cached_rank_address |
            | R21    | R20     | 16                  |
            | R22    | R20     | 16                  |

    Scenario: Admin levels cannot overtake each other due to place address ranks even when slightly misaligned
        Given the named places
          | osm | class    | type           | admin | extra+place  | geometry |
          | R20 | boundary | administrative | 6     | town         | (0 0, 0 2, 2 2, 2 0, 0 0) |
          | R21 | boundary | administrative | 8     |              | (0 0, -0.0001 1, 1 1, 1 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R20    | 12          | 16 |
          | R21    | 16          | 18 |
        Then place_addressline contains
            | object | address | cached_rank_address |
            | R21    | R20     | 16                  |

    Scenario: Admin levels must not be larger than 25
        Given the named places
          | osm | class    | type           | admin | extra+place   | geometry |
          | R20 | boundary | administrative | 6     | neighbourhood | (0 0, 0 2, 2 2, 2 0, 0 0) |
          | R21 | boundary | administrative | 7     |               | (0 0, 0 1, 1 1, 1 0, 0 0) |
          | R22 | boundary | administrative | 8     |               | (0 0, 0 0.5, 0.5 0.5, 0.5 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R20    | 12          | 22 |
          | R21    | 14          | 24 |
          | R22    | 16          | 25 |

    Scenario: admin levels contained in a place area must not overtake address ranks
        Given the named places
            | osm | class    | type           | admin | geometry |
            | R10 | place    | city           | 15    | (0 0, 0 2, 2 0, 0 0) |
            | R20 | boundary | administrative | 6     | (0 0, 0 1, 1 0, 0 0) |
        When importing
        Then placex contains
            | object | rank_search | rank_address |
            | R10    | 16          | 16           |
            | R20    | 12          | 18           |

    Scenario: admin levels overlapping a place area are not demoted
        Given the named places
            | osm | class    | type           | admin | geometry |
            | R10 | place    | city           | 15    | (0 0, 0 2, 2 0, 0 0) |
            | R20 | boundary | administrative | 6     | (-1 0, 0 1, 1 0, -1 0) |
        When importing
        Then placex contains
            | object | rank_search | rank_address |
            | R10    | 16          | 16           |
            | R20    | 12          | 12           |

    Scenario: admin levels with equal area as a place area are not demoted
        Given the named places
            | osm | class    | type           | admin | geometry |
            | R10 | place    | city           | 15    | (0 0, 0 2, 2 0, 0 0) |
            | R20 | boundary | administrative | 6     | (0 0, 0 2, 2 0, 0 0) |
        When importing
        Then placex contains
            | object | rank_search | rank_address |
            | R10    | 16          | 16           |
            | R20    | 12          | 12           |


    Scenario: adjacent admin_levels are considered the same object when they have the same wikidata
        Given the named places
          | osm | class    | type           | admin | extra+wikidata | geometry |
          | N20 | place    | square         | 15    | Q123           | 0.1 0.1  |
          | R23 | boundary | administrative | 10    | Q444           | (0 0, 0 1, 1 1, 1 0, 0 0) |
          | R21 | boundary | administrative | 9     | Q444           | (0 0, 0 1, 1 1, 1 0, 0 0) |
          | R22 | boundary | administrative | 8     | Q444           | (0 0, 0 1, 1 1, 1 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R23    | 20          | 0  |
          | R21    | 18          | 0  |
          | R22    | 16          | 16 |
        Then place_addressline contains
            | object | address | cached_rank_address |
            | N20    | R22     | 16                  |
        Then place_addressline doesn't contain
            | object | address |
            | N20    | R21     |
            | N20    | R23     |

    Scenario: adjacent admin_levels are considered different objects when they have different wikidata
        Given the named places
          | osm | class    | type           | admin | extra+wikidata | geometry |
          | N20 | place    | square         | 15    | Q123           | 0.1 0.1  |
          | R21 | boundary | administrative | 9     | Q4441          | (0 0, 0 1, 1 1, 1 0, 0 0) |
          | R22 | boundary | administrative | 8     | Q444           | (0 0, 0 1, 1 1, 1 0, 0 0) |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | R21    | 18          | 18 |
          | R22    | 16          | 16 |
        Then place_addressline contains
            | object | address | cached_rank_address |
            | N20    | R22     | 16                  |
            | N20    | R21     | 18                  |


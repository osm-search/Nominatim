Feature: Updates for address computation
    Tests for correctly updating address assignments on changes.

    Scenario: Address gets updated when an area is extended
        Given the 0.0001 grid
            | 1 |   | 2 |   | 3 |   | 4 |
            |   |   |   | 9 |   |   |   |
            | 8 |   | 7 |   | 6 |   | 5 |
        And the places
            | osm | class    | type           | admin | name | geometry    |
            | R1  | boundary | administrative | 6     | Fooo | (1,4,5,8,1) |
            | R2  | boundary | administrative | 8     | Barr | (3,4,5,6,3) |
        And the named places
            | osm | class | type   | geometry |
            | N1  | place | suburb | 9        |
        When importing
        Then place_addressline contains exactly
            | object | address |
            | N1     | R1      |
            | R2     | R1      |

        When updating places
            | osm | class    | type           | admin | name | geometry    |
            | R2  | boundary | administrative | 8     | Barr | (2,4,5,7,2) |
        Then place_addressline contains exactly
            | object | address |
            | N1     | R1      |
            | N1     | R2      |
            | R2     | R1      |

    Scenario: Address gets updated when an area is reduced
        Given the 0.0001 grid
            | 1 |   | 2 |   | 3 |   | 4 |
            |   |   |   | 9 |   |   |   |
            | 8 |   | 7 |   | 6 |   | 5 |
        And the places
            | osm | class    | type           | admin | name | geometry    |
            | R1  | boundary | administrative | 6     | Fooo | (1,4,5,8,1) |
            | R2  | boundary | administrative | 8     | Barr | (2,4,5,7,2) |
        And the named places
            | osm | class | type   | geometry |
            | N1  | place | suburb | 9        |
        When importing
        Then place_addressline contains exactly
            | object | address |
            | N1     | R1      |
            | N1     | R2      |
            | R2     | R1      |

        When updating places
            | osm | class    | type           | admin | name | geometry    |
            | R2  | boundary | administrative | 8     | Barr | (3,4,5,6,3) |
        Then place_addressline contains exactly
            | object | address |
            | N1     | R1      |
            | R2     | R1      |

    Scenario: Address gets updated when an area disappears
        Given the 0.0001 grid
            | 1 |   | 2 |   | 3 |   | 4 |
            |   |   |   | 9 |   |   |   |
            | 8 |   | 7 |   | 6 |   | 5 |
        And the places
            | osm | class    | type           | admin | name | geometry    |
            | R1  | boundary | administrative | 6     | Fooo | (1,4,5,8,1) |
            | R2  | boundary | administrative | 8     | Barr | (2,4,5,7,2) |
        And the named places
            | osm | class | type   | geometry |
            | N1  | place | suburb | 9        |
        When importing
        Then place_addressline contains exactly
            | object | address |
            | N1     | R1      |
            | N1     | R2      |
            | R2     | R1      |

        When updating places
            | osm | class    | type           | admin | name | geometry    |
            | R2  | boundary | administrative | 15    | Barr | (2,4,5,7,2) |
        Then place_addressline contains exactly
            | object | address |
            | N1     | R1      |
            | R2     | R1      |
            | R2     | N1      |

    Scenario: Address gets updated when the admin level changes
        Given the 0.0001 grid
            | 1 |   | 2 |   | 3 |   | 4 |
            |   |   |   | 9 |   |   |   |
            | 8 |   | 7 |   | 6 |   | 5 |
        And the places
            | osm | class    | type           | admin | name | geometry    |
            | R1  | boundary | administrative | 6     | Fooo | (1,4,5,8,1) |
            | R2  | boundary | administrative | 8     | Barr | (2,4,5,7,2) |
        And the named places
            | osm | class | type   | geometry |
            | N1  | place | suburb | 9        |
        When importing
        Then place_addressline contains exactly
            | object | address | cached_rank_address |
            | N1     | R1      | 12 |
            | N1     | R2      | 16 |
            | R2     | R1      | 12 |

        When updating places
            | osm | class    | type           | admin | name | geometry    |
            | R1  | boundary | administrative | 5     | Fooo | (1,4,5,8,1) |
        Then place_addressline contains exactly
            | object | address | cached_rank_address |
            | N1     | R1      | 10 |
            | N1     | R2      | 16 |
            | R2     | R1      | 10 |

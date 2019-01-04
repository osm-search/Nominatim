@DB
Feature: Import of postcodes
    Tests for postcode estimation

    Scenario: Postcodes on the object are preferred over those on the address
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
            | R4  | boundary | administrative | 10    | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type        | addr+postcode | geometry |
            | W93 | highway  | residential | 112 DE 344    | :w2N     |
            | W22 | building | yes         | 112 DE 344N   | :building:w2N |
        When importing
        Then placex contains
            | object | postcode    |
            | W22    | 112 DE 344N |
            | W93    | 112 DE 344  |
            | R4     | 112 DE 34   |
            | R34    | 112 DE      |
            | R1     | 112         |

    Scenario: Postcodes from a road are inherited by an attached building
        Given the scene admin-areas
        And the named places
            | osm | class    | type        | addr+postcode | geometry |
            | W93 | highway  | residential | 86034         | :w2N     |
        And the named places
            | osm | class    | type  | geometry |
            | W22 | building | yes   | :building:w2N |
        When importing
        Then placex contains
            | object | postcode | parent_place_id |
            | W22    | 86034    | W93 |

    Scenario: Postcodes from the lowest admin area are inherited by ways
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
            | R4  | boundary | administrative | 10    | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        When importing
        Then placex contains
            | object | postcode  |
            | W93    | 112 DE 34 |

    Scenario: Postcodes from the lowest admin area with postcode are inherited by ways
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
        And the named places
            | osm | class    | type           | admin | geometry |
            | R4  | boundary | administrative | 10    | :b2:N    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        When importing
        Then placex contains
            | object | postcode | parent_place_id |
            | W93    | 112 DE   | R4 |

    Scenario: Postcodes from the lowest admin area are inherited by buildings
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
            | R4  | boundary | administrative | 10    | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type  | geometry |
            | W22 | building | yes   | :building:w2N |
        When importing
        Then placex contains
            | object | postcode  |
            | W22    | 112 DE 34 |

    Scenario: Roads get postcodes from nearby named buildings without other info
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        And the named places
            | osm | class    | type        | addr+postcode | geometry |
            | W22 | building | yes         | 445023        | :building:w2N |
        When importing
        Then placex contains
            | object | postcode |
            | W93    | 445023   |

    Scenario: Roads get postcodes from nearby unnamed buildings without other info
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        And the named places
            | osm | class    | type        | addr+postcode | geometry |
            | W22 | place    | postcode    | 445023        | :building:w2N |
        When importing
        Then placex contains
            | object | postcode |
            | W93    | 445023   |

    Scenario: Postcodes from admin boundaries are preferred over estimated postcodes
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
            | R4  | boundary | administrative | 10    | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        And the named places
            | osm | class    | type        | addr+postcode | geometry |
            | W22 | building | yes         | 445023        | :building:w2N |
        When importing
        Then placex contains
            | object | postcode  |
            | W93    | 112 DE 34 |

    Scenario: Postcodes are added to the postcode and word table
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              |country:de |
        When importing
        Then location_postcode contains exactly
           | country | postcode | geometry |
           | de      | 01982    | country:de |
        And word contains
           | word  | class | type |
           | 01982 | place | postcode |

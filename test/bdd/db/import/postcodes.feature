@DB
Feature: Import of postcodes
    Tests for postcode estimation

    Scenario: Postcodes on the object are preferred over those on the address
        Given the grid with origin FR
            | 1 |    |    |    | 4 |  | 6 | | 8 |
            |   | 10 |    | 11 |   |  |   | |   |
            |   |    | 22 |    |   |  |   | |   |
            | 2 |    |    |    | 3 |  | 5 | | 7 |
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry    |
            | R1  | boundary | administrative | 6     | 10000         | (1,8,7,2,1) |
            | R34 | boundary | administrative | 8     | 11000         | (1,6,5,2,1) |
            | R4  | boundary | administrative | 10    | 11200         | (1,4,3,2,1) |
        And the named places
            | osm | class    | type        | addr+postcode | geometry |
            | W93 | highway  | residential | 11250         | 10,11    |
            | N22 | building | yes         | 11254         | 22       |
        When importing
        Then placex contains
            | object | postcode |
            | N22    | 11254    |
            | W93    | 11250    |
            | R4     | 11200    |
            | R34    | 11000    |
            | R1     | 10000    |

    Scenario: Postcodes from a road are inherited by an attached building
        Given the grid with origin DE
            | 10 |   |   |   | 11 |
            |    | 1 | 2 |   |    |
            |    | 4 | 3 |   |    |
        And the named places
            | osm | class    | type        | addr+postcode | geometry |
            | W93 | highway  | residential | 86034         | 10,11    |
        And the named places
            | osm | class    | type  | geometry    |
            | W22 | building | yes   | (1,2,3,4,1) |
        When importing
        Then placex contains
            | object | postcode | parent_place_id |
            | W22    | 86034    | W93 |

    Scenario: Postcodes from the lowest admin area are inherited by ways
        Given the grid with origin FR
            | 1 |    |    |    | 4 |  | 6 | | 8 |
            |   | 10 |    | 11 |   |  |   | |   |
            | 2 |    |    |    | 3 |  | 5 | | 7 |
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 10000         | (1,8,7,2,1) |
            | R34 | boundary | administrative | 8     | 11000         | (1,6,5,2,1) |
            | R4  | boundary | administrative | 10    | 11200         | (1,4,3,2,1) |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | 10,11    |
        When importing
        Then placex contains
            | object | postcode |
            | W93    | 11200    |

    Scenario: Postcodes from the lowest admin area with postcode are inherited by ways
        Given the grid with origin FR
            | 1 |    |    |    | 4 |  | 6 | | 8 |
            |   | 10 |    | 11 |   |  |   | |   |
            | 2 |    |    |    | 3 |  | 5 | | 7 |
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 10000         | (1,8,7,2,1) |
            | R34 | boundary | administrative | 8     | 11000         | (1,6,5,2,1) |
        And the named places
            | osm | class    | type           | admin | geometry    |
            | R4  | boundary | administrative | 10    | (1,4,3,2,1) |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | 10,11    |
        When importing
        Then placex contains
            | object | postcode | parent_place_id |
            | W93    | 11000    | R4 |

    Scenario: Postcodes from the lowest admin area are inherited by buildings
        Given the grid with origin FR
            | 1 |    |    |    | 4 |  | 6 | | 8 |
            |   | 10 |    | 11 |   |  |   | |   |
            |   | 13 |    | 12 |   |  |   | |   |
            | 2 |    |    |    | 3 |  | 5 | | 7 |
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 10000         | (1,8,7,2,1) |
            | R34 | boundary | administrative | 8     | 11000         | (1,6,5,2,1) |
            | R4  | boundary | administrative | 10    | 11200         | (1,4,3,2,1) |
        And the named places
            | osm | class    | type  | geometry |
            | W22 | building | yes   | (10,11,12,13,10) |
        When importing
        Then placex contains
            | object | postcode |
            | W22    | 11200    |

    Scenario: Roads get postcodes from nearby named buildings without other info
        Given the grid with origin US
            | 10 |   |   |   | 11 |
            |    | 1 | 2 |   |    |
            |    | 4 | 3 |   |    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | 10,11    |
        And the named places
            | osm | class    | type        | addr+postcode | geometry    |
            | W22 | building | yes         | 45023         | (1,2,3,4,1) |
        When importing
        Then placex contains
            | object | postcode |
            | W93    | 45023    |

    Scenario: Roads get postcodes from nearby unnamed buildings without other info
        Given the grid with origin US
            | 10 |   |   |   | 11 |
            |    | 1 | 2 |   |    |
            |    | 4 | 3 |   |    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | 10,11    |
        And the places
            | osm | class    | type        | addr+postcode | geometry    |
            | W22 | place    | postcode    | 45023         | (1,2,3,4,1) |
        When importing
        Then placex contains
            | object | postcode |
            | W93    | 45023    |

    Scenario: Postcodes from admin boundaries are preferred over estimated postcodes
        Given the grid with origin FR
            | 1 |    |    |    | 4 |  | 6 | | 8 |
            |   | 10 |    | 11 |   |  |   | |   |
            |   |    | 22 |    |   |  |   | |   |
            | 2 |    |    |    | 3 |  | 5 | | 7 |
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 10000         | (1,8,7,2,1) |
            | R34 | boundary | administrative | 8     | 11000         | (1,6,5,2,1) |
            | R4  | boundary | administrative | 10    | 11200         | (1,4,3,2,1) |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | 10,1     |
        And the named places
            | osm | class    | type        | addr+postcode |
            | N22 | building | yes         | 45023         |
        When importing
        Then placex contains
            | object | postcode |
            | W93    | 11200    |

    Scenario: Postcodes are added to the postcode and word table
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              |country:de |
        When importing
        Then location_postcode contains exactly
           | country | postcode | geometry |
           | de      | 01982    | country:de |
        And there are word tokens for postcodes 01982

    Scenario: Different postcodes with the same normalization can both be found
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | EH4 7EA       | 111              | country:gb |
           | N35 | place | house | E4 7EA        | 111              | country:gb |
        When importing
        Then location_postcode contains exactly
           | country | postcode | geometry |
           | gb      | EH4 7EA  | country:gb |
           | gb      | E4 7EA   | country:gb |
        When sending search query "EH4 7EA"
        Then results contain
           | type     | display_name |
           | postcode | EH4 7EA      |
        When sending search query "E4 7EA"
        Then results contain
           | type     | display_name |
           | postcode | E4 7EA       |

    Scenario: search and address ranks for GB post codes correctly assigned
        Given the places
         | osm  | class | type     | postcode | geometry |
         | N1   | place | postcode | E45 2CD  | country:gb |
         | N2   | place | postcode | E45 2    | country:gb |
         | N3   | place | postcode | Y45      | country:gb |
        When importing
        Then location_postcode contains exactly
         | postcode | country | rank_search | rank_address |
         | E45 2CD  | gb      | 25          | 5 |
         | E45 2    | gb      | 23          | 5 |
         | Y45      | gb      | 21          | 5 |

    Scenario: wrongly formatted GB postcodes are down-ranked
        Given the places
         | osm  | class | type     | postcode | geometry |
         | N1   | place | postcode | EA452CD  | country:gb |
         | N2   | place | postcode | E45 23   | country:gb |
        When importing
        Then location_postcode contains exactly
         | postcode | country | rank_search | rank_address |
         | EA452CD  | gb      | 30          | 30 |
         | E45 23   | gb      | 30          | 30 |

    Scenario: search and address rank for DE postcodes correctly assigned
        Given the places
         | osm | class | type     | postcode | geometry |
         | N1  | place | postcode | 56427    | country:de |
         | N2  | place | postcode | 5642     | country:de |
         | N3  | place | postcode | 5642A    | country:de |
         | N4  | place | postcode | 564276   | country:de |
        When importing
        Then location_postcode contains exactly
         | postcode | country | rank_search | rank_address |
         | 56427    | de      | 21          | 11 |
         | 5642     | de      | 30          | 30 |
         | 5642A    | de      | 30          | 30 |
         | 564276   | de      | 30          | 30 |

    Scenario: search and address rank for other postcodes are correctly assigned
        Given the places
         | osm | class | type     | postcode | geometry |
         | N1  | place | postcode | 1        | country:ca |
         | N2  | place | postcode | X3       | country:ca |
         | N3  | place | postcode | 543      | country:ca |
         | N4  | place | postcode | 54dc     | country:ca |
         | N5  | place | postcode | 12345    | country:ca |
         | N6  | place | postcode | 55TT667  | country:ca |
         | N7  | place | postcode | 123-65   | country:ca |
         | N8  | place | postcode | 12 445 4 | country:ca |
         | N9  | place | postcode | A1:bc10  | country:ca |
        When importing
        Then location_postcode contains exactly
         | postcode | country | rank_search | rank_address |
         | 1        | ca      | 21          | 11 |
         | X3       | ca      | 21          | 11 |
         | 543      | ca      | 21          | 11 |
         | 54DC     | ca      | 21          | 11 |
         | 12345    | ca      | 21          | 11 |
         | 55TT667  | ca      | 21          | 11 |
         | 123-65   | ca      | 25          | 11 |
         | 12 445 4 | ca      | 25          | 11 |
         | A1:BC10  | ca      | 25          | 11 |



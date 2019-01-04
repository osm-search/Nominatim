@DB
Feature: Update of postcode
    Tests for updating of data related to postcodes

    Scenario: A new postcode appears in the postcode and word table
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              |country:de |
        When importing
        Then location_postcode contains exactly
           | country | postcode | geometry |
           | de      | 01982    | country:de |
        When updating places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N35 | place | house | 4567          | 5                |country:ch |
        And updating postcodes
        Then location_postcode contains exactly
           | country | postcode | geometry |
           | de      | 01982    | country:de |
           | ch      | 4567     | country:ch |
        And word contains
           | word  | class | type |
           | 01982 | place | postcode |
           | 4567  | place | postcode |

     Scenario: When the last postcode is deleted, it is deleted from postcode and word
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              |country:de |
           | N35 | place | house | 4567          | 5                |country:ch |
        When importing
        And marking for delete N34
        And updating postcodes
        Then location_postcode contains exactly
           | country | postcode | geometry |
           | ch      | 4567     | country:ch |
        And word contains not
           | word  | class | type |
           | 01982 | place | postcode |
        And word contains
           | word  | class | type |
           | 4567  | place | postcode |

     Scenario: A postcode is not deleted from postcode and word when it exist in another country
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              |country:de |
           | N35 | place | house | 01982         | 5                |country:ch |
        When importing
        And marking for delete N34
        And updating postcodes
        Then location_postcode contains exactly
           | country | postcode | geometry |
           | ch      | 01982    | country:ch |
        And word contains
           | word  | class | type |
           | 01982 | place | postcode |


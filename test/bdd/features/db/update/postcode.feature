Feature: Update of postcode
    Tests for updating of data related to postcodes

     Scenario: Updating postcode in postcode boundaries without ref
        Given the grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 12345    | (1,2,3,4,1) |
        When importing
        And geocoding "12345"
        Then result 0 contains
         | object |
         | R1 |
        When updating places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 54321    | (1,2,3,4,1) |
        And geocoding "12345"
        Then exactly 0 results are returned
        When geocoding "54321"
        Then result 0 contains
         | object |
         | R1 |

    Scenario: A new postcode appears in the postcode table
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              | country:de |
        When importing
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt |
           | de           | 01982    | country:de |
        When updating places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N35 | place | house | 4567          | 5                | country:ch |
        And updating postcodes
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt |
           | de           | 01982    | country:de |
           | ch           | 4567     | country:ch |

     Scenario: When the last postcode is deleted, it is deleted from postcode
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              | country:de |
           | N35 | place | house | 4567          | 5                | country:ch |
        When importing
        And marking for delete N34
        And updating postcodes
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt |
           | ch           | 4567     | country:ch |

     Scenario: A postcode is not deleted from postcode when it exist in another country
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              | country:de |
           | N35 | place | house | 01982         | 5                | country:fr |
        When importing
        And marking for delete N34
        And updating postcodes
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt|
           | fr           | 01982    | country:fr |

     Scenario: Updating a postcode is reflected in postcode table
        Given the places
           | osm | class | type     | addr+postcode |  geometry |
           | N34 | place | postcode | 01982         | country:de |
        When importing
        And updating places
           | osm | class | type     | addr+postcode |  geometry |
           | N34 | place | postcode | 20453         | country:de |
        And updating postcodes
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt |
           | de           | 20453    | country:de |

     Scenario: When changing from a postcode type, the entry appears in placex
        When importing
        And updating places
           | osm | class | type     | addr+postcode |  geometry |
           | N34 | place | postcode | 01982         | country:de |
        Then placex has no entry for N34
        When updating places
           | osm | class | type  | addr+postcode | housenr |  geometry |
           | N34 | place | house | 20453         | 1       | country:de |
        Then placex contains
           | object | addr+housenumber | geometry!wkt |
           | N34    | 1                | country:de |
        And place contains exactly
           | osm_type | osm_id | class | type  |
           | N        | 34     | place | house |
        When updating postcodes
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt |
           | de           | 20453    | country:de |

     Scenario: When changing to a postcode type, the entry disappears from placex
        When importing
        And updating places
           | osm | class | type  | addr+postcode | housenr |  geometry |
           | N34 | place | house | 20453         | 1       | country:de |
        Then placex contains
           | object | addr+housenumber | geometry!wkt |
           | N34    | 1                | country:de|
        When updating places
           | osm | class | type     | addr+postcode |  geometry |
           | N34 | place | postcode | 01982         | country:de |
        Then placex has no entry for N34
        And place contains exactly
           | osm_type | osm_id | class | type     |
           | N        | 34     | place | postcode |
        When updating postcodes
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt |
           | de           | 01982    | country:de |

    Scenario: When a parent is deleted, the postcode gets a new parent
        Given the grid with origin DE
           | 1 |   | 3 | 4 |
           |   | 9 |   |   |
           | 2 |   | 5 | 6 |
        Given the places
           | osm | class    | type           | name  | admin | geometry    |
           | R1  | boundary | administrative | Big   | 6     | (1,4,6,2,1) |
           | R2  | boundary | administrative | Small | 6     | (1,3,5,2,1) |
        Given the places
           | osm | class | type     | addr+postcode | geometry |
           | N9  | place | postcode | 12345         | 9        |
        When importing
        Then location_postcode contains exactly
           | postcode | geometry!wkt | parent_place_id |
           | 12345    | 9            | R2              |
        When marking for delete R2
        Then location_postcode contains exactly
           | country_code | postcode | geometry!wkt | parent_place_id |
           | de           | 12345    | 9            | R1              |

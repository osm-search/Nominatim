Feature: Update of postcode
    Tests for updating of data related to postcodes

     Scenario: Updating postcode in postcode boundaries without ref
        Given the grid with origin FR
          | 1 |   | 2 |
          |   | 9 |   |
          | 4 |   | 3 |
        Given the postcodes
          | osm | postcode | centroid | geometry |
          | R1  | 12345    | 9        | (1,2,3,4,1) |
        When importing
        And geocoding "12345"
        Then result 0 contains
         | object |
         | R1 |
        Given the postcodes
          | osm | postcode | centroid | geometry |
          | R1  | 54321    | 9        | (1,2,3,4,1) |
        When refreshing postcodes
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
        Then location_postcodes contains exactly
           | country_code | postcode | centroid!wkt |
           | de           | 01982    | country:de |
        Given the postcodes
           | osm | postcode | centroid   |
           | N66 | 99201    | country:fr |
        When updating places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N35 | place | house | 4567          | 5                | country:ch |
        And refreshing postcodes
        Then location_postcodes contains exactly
           | country_code | postcode | centroid!wkt |
           | de           | 01982    | country:de |
           | ch           | 4567     | country:ch |
           | fr           | 99201    | country:fr |

     Scenario: When the last postcode is deleted, it is deleted from postcode
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              | country:de |
           | N35 | place | house | 4567          | 5                | country:ch |
        When importing
        And marking for delete N34
        And refreshing postcodes
        Then location_postcodes contains exactly
           | country_code | postcode | centroid!wkt |
           | ch           | 4567     | country:ch |

     Scenario: A postcode is not deleted from postcode when it exist in another country
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | 01982         | 111              | country:de |
           | N35 | place | house | 01982         | 5                | country:fr |
        When importing
        And marking for delete N34
        And refreshing postcodes
        Then location_postcodes contains exactly
           | country_code | postcode | centroid!wkt|
           | fr           | 01982    | country:fr |

     Scenario: Updating a postcode is reflected in postcode table
        Given the places
           | osm | class | type     | addr+postcode | geometry |
           | N34 | place | postcode | 01982         | country:de |
        When importing
        And updating places
           | osm | class | type     | addr+postcode |  geometry |
           | N34 | place | postcode | 20453         | country:de |
        And refreshing postcodes
        Then location_postcodes contains exactly
           | country_code | postcode | centroid!wkt |
           | de           | 20453    | country:de |

    Scenario: When a parent is deleted, the postcode gets a new parent
        Given the grid with origin DE
           | 1 |   | 3 | 4 |
           |   | 9 |   |   |
           | 2 |   | 5 | 6 |
        Given the places
           | osm | class    | type           | name  | admin | geometry    |
           | R1  | boundary | administrative | Big   | 6     | (1,4,6,2,1) |
           | R2  | boundary | administrative | Small | 6     | (1,3,5,2,1) |
        Given the postcodes
           | osm | postcode | centroid |
           | N9  | 12345    | 9        |
        When importing
        Then location_postcodes contains exactly
           | postcode | centroid!wkt | parent_place_id |
           | 12345    | 9            | R2              |
        When marking for delete R2
        Then location_postcodes contains exactly
           | country_code | postcode | centroid!wkt | parent_place_id |
           | de           | 12345    | 9            | R1              |

    Scenario: When a postcode area appears, postcode points are shadowed
        Given the grid with origin DE
           | 1 |   | 3 |   |
           |   | 9 |   | 8 |
           | 2 |   | 5 |   |
        Given the postcodes
           | osm | postcode | centroid |
           | N92 | 44321    | 9        |
           | N4  | 00245    | 8        |
        When importing
        Then location_postcodes contains exactly
           | country_code | postcode | osm_id | centroid!wkt |
           | de           | 44321    | -      | 9            |
           | de           | 00245    | -      | 8            |
        Given the postcodes
           | osm | postcode | centroid | geometry    |
           | R45 | 00245    | 9        | (1,3,5,2,1) |
        When refreshing postcodes
        Then location_postcodes contains exactly
           | country_code | postcode | osm_id | centroid!wkt |
           | de           | 00245    | 45     | 9            |

    Scenario: When a postcode area disappears, postcode points are unshadowed
        Given the grid with origin DE
           | 1 |   | 3 |   |
           |   | 9 |   | 8 |
           | 2 |   | 5 |   |
        Given the postcodes
           | osm | postcode | centroid | geometry    |
           | R45 | 00245    | 9        | (1,3,5,2,1) |
        Given the postcodes
           | osm | postcode | centroid |
           | N92 | 44321    | 9        |
           | N4  | 00245    | 8        |
        When importing
        Then location_postcodes contains exactly
           | country_code | postcode | osm_id | centroid!wkt |
           | de           | 00245    | 45     | 9            |
        When marking for delete R45
        And refreshing postcodes
        Then location_postcodes contains exactly
           | country_code | postcode | osm_id | centroid!wkt |
           | de           | 44321    | -      | 9            |
           | de           | 00245    | -      | 8            |

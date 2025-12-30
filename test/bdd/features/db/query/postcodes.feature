Feature: Querying fo postcode variants

    Scenario: Postcodes in Singapore (6-digit postcode)
        Given the grid with origin SG
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name   | addr+postcode | geometry |
            | W1  | highway | path | Lorang | 399174        | 10,11    |
        When importing
        When geocoding "399174"
        Then result 0 contains
            | type     | display_name |
            | postcode | 399174, Singapore |


    Scenario Outline: Postcodes in the Netherlands (mixed postcode with spaces)
        Given the grid with origin NL
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name     | addr+postcode | geometry |
            | W1  | highway | path | De Weide | <postcode>    | 10,11    |
        When importing
        When geocoding "3993 DX"
        Then result 0 contains
            | type     | display_name |
            | postcode | 3993 DX, Nederland      |
        When geocoding "3993dx"
        Then result 0 contains
            | type     | display_name |
            | postcode | 3993 DX, Nederland      |

        Examples:
            | postcode |
            | 3993 DX  |
            | 3993DX   |
            | 3993 dx  |


    Scenario: Postcodes in Singapore (6-digit postcode)
        Given the grid with origin SG
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name   | addr+postcode | geometry |
            | W1  | highway | path | Lorang | 399174        | 10,11    |
        When importing
        When geocoding "399174"
        Then result 0 contains
            | type     | display_name |
            | postcode | 399174, Singapore       |


    Scenario Outline: Postcodes in Andorra (with country code)
        Given the grid with origin AD
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name   | addr+postcode | geometry |
            | W1  | highway | path | Lorang | <postcode>    | 10,11    |
        When importing
        When geocoding "675"
        Then result 0 contains
            | type     | display_name |
            | postcode | AD675, Andorra |
        When geocoding "AD675"
        Then result 0 contains
            | type     | display_name |
            | postcode | AD675, Andorra |

        Examples:
            | postcode |
            | 675      |
            | AD 675   |
            | AD675    |


    Scenario: Different postcodes with the same normalization can both be found
        Given the places
           | osm | class | type  | addr+postcode | addr+housenumber | geometry |
           | N34 | place | house | EH4 7EA       | 111              | country:gb |
           | N35 | place | house | E4 7EA        | 111              | country:gb |
        When importing
        Then location_postcodes contains exactly
           | country_code | postcode | centroid!wkt |
           | gb           | EH4 7EA  | country:gb |
           | gb           | E4 7EA   | country:gb |
        When geocoding "EH4 7EA"
        Then result 0 contains
           | type     | display_name |
           | postcode | EH4 7EA, United Kingdom |
        When geocoding "E4 7EA"
        Then result 0 contains
           | type     | display_name |
           | postcode | E4 7EA, United Kingdom |

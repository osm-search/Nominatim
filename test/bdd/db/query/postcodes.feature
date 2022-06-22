@DB
Feature: Querying fo postcode variants

    Scenario: Postcodes in Singapore (6-digit postcode)
        Given the grid with origin SG
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name   | addr+postcode | geometry |
            | W1  | highway | path | Lorang | 399174        | 10,11    |
        When importing
        When sending search query "399174"
        Then results contain
            | ID | type     | display_name |
            | 0  | postcode | 399174       |


    @fail-legacy
    Scenario Outline: Postcodes in the Netherlands (mixed postcode with spaces)
        Given the grid with origin NL
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name     | addr+postcode | geometry |
            | W1  | highway | path | De Weide | 3993 DX       | 10,11    |
        When importing
        When sending search query "3993 DX"
        Then results contain
            | ID | type     | display_name |
            | 0  | postcode | 3993 DX      |
        When sending search query "3993dx"
        Then results contain
            | ID | type     | display_name |
            | 0  | postcode | 3993 DX      |

        Examples:
            | postcode |
            | 3993 DX  |
            | 3993DX   |
            | 3993 dx  |


    @fail-legacy
    Scenario: Postcodes in Singapore (6-digit postcode)
        Given the grid with origin SG
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name   | addr+postcode | geometry |
            | W1  | highway | path | Lorang | 399174        | 10,11    |
        When importing
        When sending search query "399174"
        Then results contain
            | ID | type     | display_name |
            | 0  | postcode | 399174       |


    @fail-legacy
    Scenario Outline: Postcodes in Andorra (with country code)
        Given the grid with origin AD
            | 10 |   |   |   | 11 |
        And the places
            | osm | class   | type | name   | addr+postcode | geometry |
            | W1  | highway | path | Lorang | <postcode>    | 10,11    |
        When importing
        When sending search query "675"
        Then results contain
            | ID | type     | display_name |
            | 0  | postcode | AD675        |
        When sending search query "AD675"
        Then results contain
            | ID | type     | display_name |
            | 0  | postcode | AD675        |

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


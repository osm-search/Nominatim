@DB
Feature: Import into placex
    Tests that data in placex is completed correctly.

    Scenario: No country code tag is available
        Given the named places
          | osm | class   | type     | geometry   |
          | N1  | highway | primary  | country:us |
        When importing
        Then placex contains
          | object | addr+country | country_code |
          | N1     | -            | us           |

    Scenario: Location overwrites country code tag
        Given the named places
          | osm | class   | type     | country | geometry |
          | N1  | highway | primary  | de      | country:us |
        When importing
        Then placex contains
          | object | addr+country | country_code |
          | N1     | de           | us           |

    Scenario: Country code tag overwrites location for countries
        Given the named places
          | osm | class    | type            | admin | country | geometry |
          | R1  | boundary | administrative  | 2     | de      | (-100 40, -101 40, -101 41, -100 41, -100 40) |
        When importing
        Then placex contains
          | object | rank_search| addr+country | country_code |
          | R1     | 4          | de           | de           |

    Scenario: Illegal country code tag for countries is ignored
        Given the named places
          | osm | class    | type            | admin | country | geometry |
          | R1  | boundary | administrative  | 2     | xx      | (-100 40, -101 40, -101 41, -100 41, -100 40) |
        When importing
        Then placex contains
          | object | addr+country | country_code |
          | R1     | xx           | us           |

    Scenario: admin level is copied over
        Given the named places
          | osm | class | type      | admin |
          | N1  | place | state     | 3     |
        When importing
        Then placex contains
          | object | admin_level |
          | N1     | 3           |

    Scenario: postcode node without postcode is dropped
        Given the places
          | osm | class   | type     | name+ref |
          | N1  | place   | postcode | 12334    |
        When importing
        Then placex has no entry for N1

    Scenario: postcode boundary without postcode is dropped
        Given the places
          | osm | class    | type        | name+ref | geometry |
          | R1  | boundary | postal_code | 554476   | poly-area:0.1 |
        When importing
        Then placex has no entry for R1

    Scenario: search and address ranks for boundaries are correctly assigned
        Given the named places
          | osm | class    | type |
          | N1  | boundary | administrative |
        And the named places
          | osm | class    | type           | geometry |
          | W10 | boundary | administrative | 10 10, 11 11 |
        And the named places
          | osm | class    | type           | admin | geometry |
          | R20 | boundary | administrative | 2     | (1 1, 2 2, 1 2, 1 1) |
          | R21 | boundary | administrative | 32    | (3 3, 4 4, 3 4, 3 3) |
          | R22 | boundary | nature_park    | 6     | (0 0, 1 0, 0 1, 0 0) |
          | R23 | boundary | natural_reserve| 10    | (0 0, 1 1, 1 0, 0 0) |
        And the named places
          | osm | class | type    | geometry |
          | R40 | place | country | (1 1, 2 2, 1 2, 1 1) |
          | R41 | place | state   | (3 3, 4 4, 3 4, 3 3) |
        When importing
        Then placex has no entry for N1
        And placex has no entry for W10
        And placex contains
          | object | rank_search | rank_address |
          | R20    | 4           | 4 |
          | R21    | 25          | 0 |
          | R22    | 25          | 0 |
          | R23    | 25          | 0 |
          | R40    | 4           | 0 |
          | R41    | 8           | 0 |

    Scenario: search and address ranks for highways correctly assigned
        Given the scene roads-with-pois
        And the places
          | osm | class    | type  |
          | N1  | highway  | bus_stop |
        And the places
          | osm | class    | type         | geometry |
          | W1  | highway  | primary      | :w-south |
          | W2  | highway  | secondary    | :w-south |
          | W3  | highway  | tertiary     | :w-south |
          | W4  | highway  | residential  | :w-north |
          | W5  | highway  | unclassified | :w-north |
          | W6  | highway  | something    | :w-north |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | N1     | 30          | 30 |
          | W1     | 26          | 26 |
          | W2     | 26          | 26 |
          | W3     | 26          | 26 |
          | W4     | 26          | 26 |
          | W5     | 26          | 26 |
          | W6     | 30          | 30 |

    Scenario: rank and inclusion of landuses
        Given the named places
          | osm | class   | type |
          | N2  | landuse | residential |
        And the named places
          | osm | class   | type        | geometry |
          | W2  | landuse | residential | 1 1, 1 1.1 |
          | W4  | landuse | residential | poly-area:0.1 |
          | R2  | landuse | residential | poly-area:0.05 |
          | R3  | landuse | forrest     | poly-area:0.5 |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | N2     | 30          | 30 |
          | W2     | 30          | 30 |
          | W4     | 22          | 22 |
          | R2     | 22          | 22 |
          | R3     | 22          |  0 |

    Scenario: rank and inclusion of naturals
       Given the named places
          | osm | class   | type |
          | N2  | natural | peak |
          | N4  | natural | volcano |
          | N5  | natural | foobar |
       And the named places
          | osm | class   | type           | geometry |
          | W2  | natural | mountain_range | 12 12,11 11 |
          | W3  | natural | foobar         | 13 13,13.1 13 |
          | R3  | natural | volcano        | poly-area:0.1 |
          | R4  | natural | foobar         | poly-area:0.5 |
          | R5  | natural | sea            | poly-area:5.0 |
          | R6  | natural | sea            | poly-area:0.01 |
       When importing
       Then placex contains
          | object | rank_search | rank_address |
          | N2     | 18          | 0 |
          | N4     | 18          | 0 |
          | N5     | 22          | 0 |
          | W2     | 18          | 0 |
          | R3     | 18          | 0 |
          | R4     | 22          | 0 |
          | R5     | 4           | 0 |
          | R6     | 4           | 0 |
          | W3     | 22          | 0 |

    Scenario: boundary ways for countries and states are ignored
        Given the named places
          | osm | class    | type           | admin | geometry |
          | W4  | boundary | administrative | 2     | poly-area:0.1 |
          | R4  | boundary | administrative | 2     | poly-area:0.1 |
          | W5  | boundary | administrative | 3     | poly-area:0.1 |
          | R5  | boundary | administrative | 3     | poly-area:0.1 |
          | W6  | boundary | administrative | 4     | poly-area:0.1 |
          | R6  | boundary | administrative | 4     | poly-area:0.1 |
          | W7  | boundary | administrative | 5     | poly-area:0.1 |
          | R7  | boundary | administrative | 5     | poly-area:0.1 |
       When importing
       Then placex contains exactly
           | object |
           | R4     |
           | R5     |
           | R6     |
           | W7     |
           | R7     |

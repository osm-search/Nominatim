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

    Scenario: search and address ranks for GB post codes correctly assigned
        Given the places
         | osm  | class | type     | postcode | geometry |
         | N1   | place | postcode | E45 2CD  | country:gb |
         | N2   | place | postcode | E45 2    | country:gb |
         | N3   | place | postcode | Y45      | country:gb |
        When importing
        Then placex contains
         | object | postcode | country_code | rank_search | rank_address |
         | N1     | E45 2CD  | gb           | 25          | 0 |
         | N2     | E45 2    | gb           | 23          | 0 |
         | N3     | Y45      | gb           | 21          | 0 |

    Scenario: wrongly formatted GB postcodes are down-ranked
        Given the places
         | osm  | class | type     | postcode | geometry |
         | N1   | place | postcode | EA452CD  | country:gb |
         | N2   | place | postcode | E45 23   | country:gb |
        When importing
        Then placex contains
         | object | country_code | rank_search | rank_address |
         | N1     | gb           | 30          | 0 |
         | N2     | gb           | 30          | 0 |

    Scenario: search and address rank for DE postcodes correctly assigned
        Given the places
         | osm | class | type     | postcode | geometry |
         | N1  | place | postcode | 56427    | country:de |
         | N2  | place | postcode | 5642     | country:de |
         | N3  | place | postcode | 5642A    | country:de |
         | N4  | place | postcode | 564276   | country:de |
        When importing
        Then placex contains
         | object | country_code | rank_search | rank_address |
         | N1     | de           | 21          | 0 |
         | N2     | de           | 30          | 0 |
         | N3     | de           | 30          | 0 |
         | N4     | de           | 30          | 0 |

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
        Then placex contains
         | object | country_code | rank_search | rank_address |
         | N1     | ca           | 21          | 0 |
         | N2     | ca           | 21          | 0 |
         | N3     | ca           | 21          | 0 |
         | N4     | ca           | 21          | 0 |
         | N5     | ca           | 21          | 0 |
         | N6     | ca           | 21          | 0 |
         | N7     | ca           | 25          | 0 |
         | N8     | ca           | 25          | 0 |
         | N9     | ca           | 25          | 0 |

    Scenario: search and address ranks for places are correctly assigned
        Given the named places
          | osm  | class     | type      |
          | N1   | foo       | bar       |
          | N11  | place     | Continent |
          | N12  | place     | continent |
          | N13  | place     | sea       |
          | N14  | place     | country   |
          | N15  | place     | state     |
          | N16  | place     | region    |
          | N17  | place     | county    |
          | N18  | place     | city      |
          | N19  | place     | island    |
          | N20  | place     | town      |
          | N21  | place     | village   |
          | N22  | place     | hamlet    |
          | N23  | place     | municipality |
          | N24  | place     | district     |
          | N25  | place     | unincorporated_area |
          | N26  | place     | borough             |
          | N27  | place     | suburb              |
          | N28  | place     | croft               |
          | N29  | place     | subdivision         |
          | N30  | place     | isolated_dwelling   |
          | N31  | place     | farm                |
          | N32  | place     | locality            |
          | N33  | place     | islet               |
          | N34  | place     | mountain_pass       |
          | N35  | place     | neighbourhood       |
          | N36  | place     | house               |
          | N37  | place     | building            |
          | N38  | place     | houses              |
        And the named places
          | osm  | class     | type      | extra+capital |
          | N101 | place     | city      | yes |
        When importing
        Then placex contains
          | object | rank_search | rank_address |
          | N1     | 30          | 30 |
          | N11    | 30          | 30 |
          | N12    | 2           | 0 |
          | N13    | 2           | 0 |
          | N14    | 4           | 0 |
          | N15    | 8           | 0 |
          | N16    | 18          | 0 |
          | N17    | 12          | 12 |
          | N18    | 16          | 16 |
          | N19    | 17          | 0 |
          | N20    | 18          | 16 |
          | N21    | 19          | 16 |
          | N22    | 19          | 16 |
          | N23    | 19          | 16 |
          | N24    | 19          | 16 |
          | N25    | 19          | 16 |
          | N26    | 19          | 16 |
          | N27    | 20          | 20 |
          | N28    | 20          | 20 |
          | N29    | 20          | 20 |
          | N30    | 20          | 20 |
          | N31    | 20          | 0 |
          | N32    | 20          | 0 |
          | N33    | 20          | 0 |
          | N34    | 20          | 0 |
          | N101   | 15          | 16 |
          | N35    | 22          | 22 |
          | N36    | 30          | 30 |
          | N37    | 30          | 30 |
          | N38    | 28          | 0 |

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
          | R21    | 30          | 30 |
          | R22    | 30          | 30 |
          | R23    | 30          | 30 |
          | R40    | 4           | 4 |
          | R41    | 8           | 8 |

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
          | N1     | 30          |  0 |
          | W1     | 26          | 26 |
          | W2     | 26          | 26 |
          | W3     | 26          | 26 |
          | W4     | 26          | 26 |
          | W5     | 26          | 26 |
          | W6     | 26          | 26 |

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
          | N2     | 30          |  0 |
          | W2     | 30          |  0 |
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
          | N5     | 30          | 30 |
          | W2     | 18          | 0 |
          | R3     | 18          | 0 |
          | R4     | 30          | 30 |
          | R5     | 4           | 0 |
          | R6     | 4           | 0 |
          | W3     | 30          | 30 |

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

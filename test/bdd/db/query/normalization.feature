@DB
Feature: Import and search of names
    Tests all naming related issues: normalisation,
    abbreviations, internationalisation, etc.

    Scenario: non-latin scripts can be found
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | Речицкий район |
          | N2  | place | locality  | Refugio de montaña |
          | N3  | place | locality  | 高槻市|
          | N4  | place | locality  | الدوحة |
        When importing
        When sending search query "Речицкий район"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "Refugio de montaña"
        Then results contain
         | ID | osm |
         | 0  | N2 |
        When sending search query "高槻市"
        Then results contain
         | ID | osm |
         | 0  | N3 |
        When sending search query "الدوحة"
        Then results contain
         | ID | osm |
         | 0  | N4 |

    Scenario: Case-insensitivity of search
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | FooBar |
        When importing
        Then placex contains
          | object | class  | type     | name+name |
          | N1     | place  | locality | FooBar |
        When sending search query "FooBar"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "foobar"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "fOObar"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "FOOBAR"
        Then results contain
         | ID | osm |
         | 0  | N1 |

    Scenario: Multiple spaces in name
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | one two  three |
        When importing
        When sending search query "one two three"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "one   two three"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "one two  three"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "    one two three"
        Then results contain
         | ID | osm |
         | 0  | N1 |

    Scenario: Special characters in name
        Given the places
          | osm | class | type      | name+name:de |
          | N1  | place | locality  | Jim-Knopf-Straße |
          | N2  | place | locality  | Smith/Weston |
          | N3  | place | locality  | space mountain |
          | N4  | place | locality  | space |
          | N5  | place | locality  | mountain |
        When importing
        When sending search query "Jim-Knopf-Str"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "Jim Knopf-Str"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "Jim Knopf Str"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "Jim/Knopf-Str"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "Jim-Knopfstr"
        Then results contain
         | ID | osm |
         | 0  | N1 |
        When sending search query "Smith/Weston"
        Then results contain
         | ID | osm |
         | 0  | N2 |
        When sending search query "Smith Weston"
        Then results contain
         | ID | osm |
         | 0  | N2 |
        When sending search query "Smith-Weston"
        Then results contain
         | ID | osm |
         | 0  | N2 |
        When sending search query "space mountain"
        Then results contain
         | ID | osm |
         | 0  | N3 |
        When sending search query "space-mountain"
        Then results contain
         | ID | osm |
         | 0  | N3 |
        When sending search query "space/mountain"
        Then results contain
         | ID | osm |
         | 0  | N3 |
        When sending search query "space\mountain"
        Then results contain
         | ID | osm |
         | 0  | N3 |
        When sending search query "space(mountain)"
        Then results contain
         | ID | osm |
         | 0  | N3 |

    Scenario: Landuse with name are found
        Given the grid
          | 1 | 2 |
          | 3 |   |
        Given the places
          | osm | class    | type        | name     | geometry |
          | R1  | natural  | meadow      | landuse1 | (1,2,3,1) |
          | R2  | landuse  | industrial  | landuse2 | (2,3,1,2) |
        When importing
        When sending search query "landuse1"
        Then results contain
         | ID | osm |
         | 0  | R1 |
        When sending search query "landuse2"
        Then results contain
         | ID | osm |
         | 0  | R2 |

    Scenario: Postcode boundaries without ref
        Given the grid with origin FR
          |   | 2 |   |
          | 1 |   | 3 |
        Given the places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 12345    | (1,2,3,1) |
        When importing
        When sending search query "12345"
        Then results contain
         | ID | osm |
         | 0  | R1 |

    Scenario: Unprintable characters in postcodes are ignored
        Given the named places
            | osm  | class   | type   | address                    | geometry   |
            | N234 | amenity | prison | 'postcode' : u'1234\u200e' | country:de |
        When importing
        And sending search query "1234"
        Then result 0 has not attributes osm_type

    Scenario Outline: Housenumbers with special characters are found
        Given the grid
            | 1 |  |   |  | 2 |
            |   |  | 9 |  |   |
        And the places
            | osm | class   | type    | name    | geometry |
            | W1  | highway | primary | Main St | 1,2      |
        And the places
            | osm | class    | type | housenr | geometry |
            | N1  | building | yes  | <nr>    | 9        |
        When importing
        And sending search query "Main St <nr>"
        Then results contain
         | osm | display_name |
         | N1  | <nr>, Main St |

    Examples:
        | nr |
        | 1  |
        | 3456 |
        | 1 a |
        | 56b |
        | 1 A |
        | 2號 |
        | 1Б  |
        | 1 к1 |
        | 23-123 |

    Scenario Outline: Housenumbers in lists are found
        Given the grid
            | 1 |  |   |  | 2 |
            |   |  | 9 |  |   |
        And the places
            | osm | class   | type    | name    | geometry |
            | W1  | highway | primary | Main St | 1,2      |
        And the places
            | osm | class    | type | housenr   | geometry |
            | N1  | building | yes  | <nr-list> | 9        |
        When importing
        And sending search query "Main St <nr>"
        Then results contain
         | osm | display_name |
         | N1  | <nr-list>, Main St |

    Examples:
        | nr-list    | nr |
        | 1,2,3      | 1  |
        | 1,2,3      | 2  |
        | 1, 2, 3    | 3  |
        | 45 ;67;3   | 45 |
        | 45 ;67;3   | 67 |
        | 1a;1k      | 1a |
        | 1a;1k      | 1k |
        | 34/678     | 34 |
        | 34/678     | 678 |
        | 34/678     | 34/678 |

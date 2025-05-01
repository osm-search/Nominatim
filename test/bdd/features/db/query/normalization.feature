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
        When geocoding "Речицкий район"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "Refugio de montaña"
        Then result 0 contains
         | object |
         | N2 |
        When geocoding "高槻市"
        Then result 0 contains
         | object |
         | N3 |
        When geocoding "الدوحة"
        Then result 0 contains
         | object |
         | N4 |

    Scenario: Case-insensitivity of search
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | FooBar |
        When importing
        Then placex contains
          | object | class  | type     | name+name |
          | N1     | place  | locality | FooBar |
        When geocoding "FooBar"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "foobar"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "fOObar"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "FOOBAR"
        Then result 0 contains
         | object |
         | N1 |

    Scenario: Multiple spaces in name
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | one two  three |
        When importing
        When geocoding "one two three"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "one   two three"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "one two  three"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "    one two three"
        Then result 0 contains
         | object |
         | N1 |

    Scenario: Special characters in name
        Given the places
          | osm | class | type      | name+name:de |
          | N1  | place | locality  | Jim-Knopf-Straße |
          | N2  | place | locality  | Smith/Weston |
          | N3  | place | locality  | space mountain |
          | N4  | place | locality  | space |
          | N5  | place | locality  | mountain |
        When importing
        When geocoding "Jim-Knopf-Str"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "Jim Knopf-Str"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "Jim Knopf Str"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "Jim/Knopf-Str"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "Jim-Knopfstr"
        Then result 0 contains
         | object |
         | N1 |
        When geocoding "Smith/Weston"
        Then result 0 contains
         | object |
         | N2 |
        When geocoding "Smith Weston"
        Then result 0 contains
         | object |
         | N2 |
        When geocoding "Smith-Weston"
        Then result 0 contains
         | object |
         | N2 |
        When geocoding "space mountain"
        Then result 0 contains
         | object |
         | N3 |
        When geocoding "space-mountain"
        Then result 0 contains
         | object |
         | N3 |
        When geocoding "space/mountain"
        Then result 0 contains
         | object |
         | N3 |
        When geocoding "space\mountain"
        Then result 0 contains
         | object |
         | N3 |
        When geocoding "space(mountain)"
        Then result 0 contains
         | object |
         | N3 |

    Scenario: Landuse with name are found
        Given the grid
          | 1 | 2 |
          | 3 |   |
        Given the places
          | osm | class    | type        | name     | geometry |
          | R1  | natural  | meadow      | landuse1 | (1,2,3,1) |
          | R2  | landuse  | industrial  | landuse2 | (2,3,1,2) |
        When importing
        When geocoding "landuse1"
        Then result 0 contains
         | object |
         | R1 |
        When geocoding "landuse2"
        Then result 0 contains
         | object |
         | R2 |

    Scenario: Postcode boundaries without ref
        Given the grid with origin FR
          |   | 2 |   |
          | 1 |   | 3 |
        Given the places
          | osm | class    | type        | postcode  | geometry |
          | R1  | boundary | postal_code | 123-45    | (1,2,3,1) |
        When importing
        When geocoding "123-45"
        Then result 0 contains
         | object |
         | R1 |

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
        And geocoding "Main St <nr>"
        Then result 0 contains
         | object | display_name |
         | N1     | <nr>, Main St |

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
        And geocoding "Main St <nr>"
        Then result 0 contains
         | object | display_name |
         | N1     | <nr-list>, Main St |

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

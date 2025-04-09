Feature: Import of address interpolations
    Tests that interpolated addresses are added correctly

    Scenario: Simple even interpolation line with two points and no street nearby
        Given the grid with origin 1,1
          | 1 |  | 9 |  | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 6       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,2      |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to no interpolation

    Scenario: Simple even interpolation line with two points
        Given the grid with origin 1,1
          | 1 |  | 9 |  | 2 |
          | 4 |  |   |  | 5 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 6       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,2      |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 4   | 9 |

    Scenario: Backwards even two point interpolation line
        Given the grid with origin 1,1
          | 1 | 8 | 9 | 2 |
          | 4 |   |   | 5 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 8       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 2,1      |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 2,1 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 6   | 8,9      |

    Scenario: Simple odd two point interpolation
        Given the grid with origin 1,1
          | 1 | 8 |  |  | 9 | 2 |
          | 4 |   |  |  | 5 |   |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 1       |
          | N2  | place | house  | 11      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | odd                | 1,2      |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 3     | 9   | 8,9      |

    Scenario: Simple all two point interpolation
        Given the grid with origin 1,1
          | 1 | 8 | 9 | 2 |
          | 4 |   |   | 5 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 1       |
          | N2  | place | house  | 4       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | all                | 1,2      |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 3   | 8,9 |

    Scenario: Even two point interpolation line with intermediate empty node
        Given the grid
          | 1 | 8 |  | 3 | 9 | 2 |
          | 4 |   |  |   | 5 |   |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 12      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2    |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 10  | 8,3,9 |

    Scenario: Even two point interpolation line with intermediate duplicated empty node
        Given the grid
          | 4 |   |   |   | 5 |
          | 1 | 8 | 3 | 9 | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2 |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,3,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 8   | 8,3,9 |

    Scenario: Simple even three point interpolation line
        Given the grid
          | 4 |   |  |   |   |   | 5 |
          | 1 | 8 |  | 9 | 3 | 7 | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 14      |
          | N3  | place | house  | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2    |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     |  8  | 8,9 |
          | 12    | 12  | 7 |

    Scenario: Simple even four point interpolation line
        Given the grid
          | 1 | 10 |   | 11 | 3 |
          |   |    |   |    | 12|
          |   |    | 4 | 13 | 2 |
        Given the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 14      |
          | N3  | place | house | 10      |
          | N4  | place | house | 18      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2,4  |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 1,3,2,4  |
        And the ways
          | id | nodes |
          | 1  | 1,3,2,4 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 8   | 10,11    |
          | 12    | 12  | 12       |
          | 16    | 16  | 13       |

    Scenario: Reverse simple even three point interpolation line
        Given the grid
          | 1 | 8  |  | 9 | 3 | 7 | 2 |
          | 4 |    |  |   |   |   | 5 |
        Given the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 14      |
          | N3  | place | house | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 2,3,1    |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 2,3,1 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     |  8  | 8,9      |
          | 12    | 12  | 7        |

    Scenario: Even three point interpolation line with odd center point
        Given the grid
          | 1 |  | 10 |  | 11 | 3 | 2 |
          | 4 |  |    |  |    |   | 5 |
        Given the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 8       |
          | N3  | place | house | 7       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2    |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 6   | 10,11 |

    Scenario: Interpolation line with self-intersecting way
        Given the grid
          | 1  | 9 | 2 |
          |    |   | 8 |
          |    |   | 3 |
        Given the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
          | N3  | place | house | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,2,3,2  |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 1,2,3    |
        And the ways
          | id | nodes |
          | 1  | 1,2,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 4   | 9        |
          | 8     | 8   | 8        |
          | 8     | 8   | 8        |

    Scenario: Interpolation line with self-intersecting way II
        Given the grid
          | 1  | 9 | 2 |
          |    |   | 3 |
        Given the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,2,3,2  |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 1,2,3    |
        And the ways
          | id | nodes |
          | 1  | 1,2,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 4   | 9        |

    Scenario: addr:street on interpolation way
        Given the grid
          |    | 1 |  | 2 |    |
          | 10 |   |  |   | 11 |
          | 20 |   |  |   | 21 |
        And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 1        |
          | N2  | place | house | 6       | 2        |
          | N3  | place | house | 12      | 1        |
          | N4  | place | house | 16      | 2        |
        And the places
          | osm | class   | type    | addr+interpolation | street       | geometry |
          | W10 | place   | houses  | even               |              | 1,2      |
          | W11 | place   | houses  | even               | Cloud Street | 1,2      |
        And the places
          | osm | class   | type     | name         | geometry |
          | W2  | highway | tertiary | Sun Way      | 10,11    |
          | W3  | highway | tertiary | Cloud Street | 20,21    |
        And the ways
          | id | nodes |
          | 10 | 1,2   |
          | 11 | 3,4   |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
          | N3     | W3 |
          | N4     | W3 |
        Then W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4 |
        Then W11 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 14    | 14 |
        When geocoding "16 Cloud Street"
        Then result 0 contains
         | object |
         | N4  |
        When geocoding "14 Cloud Street"
        Then result 0 contains
         | object |
         | W11 |

    Scenario: addr:street on housenumber way
        Given the grid
          |    | 1 |  | 2 |    |
          | 10 |   |  |   | 11 |
          | 20 |   |  |   | 21 |
        And the places
          | osm | class | type  | housenr | street       | geometry |
          | N1  | place | house | 2       |              | 1        |
          | N2  | place | house | 6       |              | 2        |
          | N3  | place | house | 12      | Cloud Street | 1        |
          | N4  | place | house | 16      | Cloud Street | 2        |
        And the places
          | osm | class   | type    | addr+interpolation | geometry |
          | W10 | place   | houses  | even               | 1,2      |
          | W11 | place   | houses  | even               | 1,2      |
        And the places
          | osm | class   | type     | name         | geometry |
          | W2  | highway | tertiary | Sun Way      | 10,11    |
          | W3  | highway | tertiary | Cloud Street | 20,21    |
        And the ways
          | id  | nodes |
          | 10  | 1,2 |
          | 11  | 3,4 |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
          | N3     | W3 |
          | N4     | W3 |
        Then W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4 |
        Then W11 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 14    | 14 |
        When geocoding "16 Cloud Street"
        Then result 0 contains
         | object |
         | N4  |
        When geocoding "14 Cloud Street"
        Then result 0 contains
         | object |
         | W11 |

    Scenario: Geometry of points and way don't match (github #253)
        Given the places
          | osm | class | type        | housenr | geometry |
          | N1  | place | house       | 10      | 144.9632341 -37.76163 |
          | N2  | place | house       | 6       | 144.9630541 -37.7628174 |
          | N3  | shop  | supermarket | 2       | 144.9629794 -37.7630755 |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even    | 144.9632341 -37.76163,144.9630541 -37.7628172,144.9629794 -37.7630755 |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 144.9632341 -37.76163,144.9629794 -37.7630755    |
        And the ways
          | id | nodes |
          | 1  | 1,2,3 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 4   | 144.96301672 -37.76294644 |
          | 8     | 8   | 144.96314407 -37.762223692 |

    Scenario: Place with missing address information
        Given the grid
          | 1 |  | 2 |  |  | 3 |
          | 4 |  |   |  |  | 5 |
        And the places
          | osm | class   | type   | housenr |
          | N1  | place   | house  | 23      |
          | N2  | amenity | school |         |
          | N3  | place   | house  | 29      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | odd                | 1,2,3 |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,2,3 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 25    | 27  | 0.0000166 0,0.00002 0,0.0000333 0 |

    Scenario: Ways without node entries are ignored
        Given the places
          | osm | class | type   | housenr | geometry |
          | W1  | place | houses | even    | 1 1, 1 1.001 |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 1 1, 1 1.001 |
        When importing
        Then W1 expands to no interpolation

    Scenario: Ways with nodes without housenumbers are ignored
        Given the grid
          | 1 |  | 2 |
          | 4 |  | 5 |
        Given the places
          | osm | class | type   |
          | N1  | place | house  |
          | N2  | place | house  |
        Given the places
          | osm | class | type   | housenr | geometry |
          | W1  | place | houses | even    | 1,2 |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        When importing
        Then W1 expands to no interpolation

    Scenario: Two point interpolation starting at 0
        Given the grid with origin 1,1
          | 1 | 10 |  |  | 11 | 2 |
          | 4 |    |  |  |    | 5 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 0       |
          | N2  | place | house  | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,2      |
        And the places
          | osm | class   | type        | name        | geometry |
          | W10 | highway | residential | London Road |4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 8   | 10,11 |
        When reverse geocoding 1,1
        Then the result contains
          | object | type  | display_name |
          | N1     | house | 0, London Road |

    Scenario: Parenting of interpolation with additional tags
        Given the grid
          | 1 |   |   |   |   |   |
          |   |   |   |   |   |   |
          |   | 8 |   |   | 9 |   |
          |   |   |   |   |   |   |
          | 2 |   |   |   |   | 3 |
        Given the places
          | osm | class | type  | housenr | addr+street |
          | N8  | place | house | 10      | Horiz St    |
          | N9  | place | house | 16      | Horiz St    |
        And the places
          | osm | class   | type        | name     | geometry |
          | W1  | highway | residential | Vert St  | 1,2      |
          | W2  | highway | residential | Horiz St | 2,3      |
        And the places
          | osm | class | type   | addr+interpolation | addr+inclusion | geometry |
          | W10 | place | houses | even               | actual         | 8,9      |
        And the ways
          | id | nodes |
          | 10 | 8,9   |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N8     | W2              |
          | N9     | W2              |
        And W10 expands to interpolation
          | start | end | parent_place_id |
          | 12    | 14  | W2              |


    Scenario Outline: Bad interpolation values are ignored
        Given the grid with origin 1,1
          | 1 |  | 9 |  | 2 |
          | 4 |  |   |  | 5 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 6       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | <value>            | 1,2      |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to no interpolation

        Examples:
          | value |
          | foo   |
          | x     |
          | 12-2  |


    Scenario: Interpolation line where points have been moved (Github #3022)
        Given the 0.00001 grid
         | 1 | | | | | | | | 2 | 3 | 9 | | | | | | | | 4 |
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 2       | 1 |
          | N2  | place | house  | 18      | 3 |
          | N3  | place | house  | 24      | 9 |
          | N4  | place | house  | 42      | 4 |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,2,3,4  |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 1,4      |
        And the ways
          | id | nodes   |
          | 1  | 1,2,3,4 |
        When importing
        Then W1 expands to interpolation
          | start | end |
          | 4     | 16  |
          | 20    | 22  |
          | 26    | 40  |


    Scenario: Interpolation line with duplicated points
        Given the grid
          | 7 | 10 | 8 | 11 | 9 |
          | 4 |    |   |    | 5 |
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 2       | 7 |
          | N2  | place | house  | 6       | 8 |
          | N3  | place | house  | 10      | 8 |
          | N4  | place | house  | 14      | 9 |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 7,8,8,9  |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 4,5      |
        And the ways
          | id | nodes   |
          | 1  | 1,2,3,4 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 4   | 10       |
          | 12    | 12  | 11       |


    Scenario: Interpolaton line with broken way geometry (Github #2986)
        Given the grid
          | 1 | 8 | 10 | 11 | 9 | 2 | 3 | 4 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 8       |
          | N3  | place | house  | 12      |
          | N4  | place | house  | 14      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 8,9      |
        And the named places
          | osm | class   | type        | geometry |
          | W10 | highway | residential | 1,4      |
        And the ways
          | id | nodes       |
          | 1  | 1,8,9,2,3,4 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 6   | 10,11    |

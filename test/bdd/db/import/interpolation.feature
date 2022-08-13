@DB
Feature: Import of address interpolations
    Tests that interpolated addresses are added correctly

    Scenario: Simple even interpolation line with two points
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
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 4   | 9 |

    Scenario: Backwards even two point interpolation line
        Given the grid with origin 1,1
          | 1 | 8 | 9 | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 8       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even    | 1,2 |
        And the ways
          | id | nodes |
          | 1  | 2,1 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 6   | 8,9 |

    Scenario: Simple odd two point interpolation
        Given the grid with origin 1,1
          | 1 | 8 |  |  | 9 | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 1       |
          | N2  | place | house  | 11      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | odd                | 1,2      |
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
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 1       |
          | N2  | place | house  | 4       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | all                | 1,2      |
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
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 12      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2    |
        And the ways
          | id | nodes |
          | 1  | 1,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 10  | 8,3,9 |

    Scenario: Even two point interpolation line with intermediate duplicated empty node
        Given the grid
          | 1 | 8 | 3 | 9 | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2 |
        And the ways
          | id | nodes |
          | 1  | 1,3,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 8   | 8,3,9 |

    Scenario: Simple even three point interpolation line
        Given the grid
          | 1 | 8 |  | 9 | 3 | 7 | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 2       |
          | N2  | place | house  | 14      |
          | N3  | place | house  | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2    |
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
        Given the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 14      |
          | N3  | place | house | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 2,3,1    |
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
          | 1 |  | 10 |  |  | 11 | 3 | 2 |
        Given the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 8       |
          | N3  | place | house | 7       |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,3,2    |
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
        When sending search query "16 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 4 |
        When sending search query "14 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | W        | 11 |

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
        When sending search query "16 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 4 |
        When sending search query "14 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | W        | 11 |

    Scenario: Geometry of points and way don't match (github #253)
        Given the places
          | osm | class | type        | housenr | geometry |
          | N1  | place | house       | 10      | 144.9632341 -37.76163 |
          | N2  | place | house       | 6       | 144.9630541 -37.7628174 |
          | N3  | shop  | supermarket | 2       | 144.9629794 -37.7630755 |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even    | 144.9632341 -37.76163,144.9630541 -37.7628172,144.9629794 -37.7630755 |
        And the ways
          | id | nodes |
          | 1  | 1,2,3 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 4     | 4   | 144.963016 -37.762946 |
          | 8     | 8   | 144.963144 -37.7622237 |

    Scenario: Place with missing address information
        Given the grid
          | 1 |  | 2 |  |  | 3 |
        And the places
          | osm | class   | type   | housenr |
          | N1  | place   | house  | 23      |
          | N2  | amenity | school |         |
          | N3  | place   | house  | 29      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | odd                | 1,2,3 |
        And the ways
          | id | nodes |
          | 1  | 1,2,3 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 25    | 27  | 0.000016 0,0.00002 0,0.000033 0 |

    Scenario: Ways without node entries are ignored
        Given the places
          | osm | class | type   | housenr | geometry |
          | W1  | place | houses | even    | 1 1, 1 1.001 |
        When importing
        Then W1 expands to no interpolation

    Scenario: Ways with nodes without housenumbers are ignored
        Given the grid
          | 1  |  |  2 |
        Given the places
          | osm | class | type   |
          | N1  | place | house  |
          | N2  | place | house  |
        Given the places
          | osm | class | type   | housenr | geometry |
          | W1  | place | houses | even    | 1,2 |
        When importing
        Then W1 expands to no interpolation

    Scenario: Two point interpolation starting at 0
        Given the grid with origin 1,1
          | 1 | 10 |  |  | 11 | 2 |
        Given the places
          | osm | class | type   | housenr |
          | N1  | place | house  | 0       |
          | N2  | place | house  | 10      |
        And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W1  | place | houses | even               | 1,2      |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 8   | 10,11 |
        When sending jsonv2 reverse coordinates 1,1
        Then results contain
          | ID | osm_type | osm_id | type  | display_name |
          | 0  | node     | 1      | house | 0 |

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

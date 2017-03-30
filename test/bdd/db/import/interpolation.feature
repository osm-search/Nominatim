@DB
Feature: Import of address interpolations
    Tests that interpolated addresses are added correctly

    Scenario: Simple even interpolation line with two points
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 2       | 1 1 |
          | N2  | place | house  | 6       | 1 1.001 |
          | W1  | place | houses | even    | 1 1, 1 1.001 |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 6   | 1 1, 1 1.001 |

    Scenario: Backwards even two point interpolation line
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 2       | 1 1 |
          | N2  | place | house  | 6       | 1 1.001 |
          | W1  | place | houses | even    | 1 1.001, 1 1 |
        And the ways
          | id | nodes |
          | 1  | 2,1 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 6   | 1 1, 1 1.001 |

    Scenario: Simple odd two point interpolation
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 1       | 1 1 |
          | N2  | place | house  | 11      | 1 1.001 |
          | W1  | place | houses | odd     | 1 1, 1 1.001 |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 1     | 11  | 1 1, 1 1.001 |

    Scenario: Simple all two point interpolation
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 1       | 1 1 |
          | N2  | place | house  | 3       | 1 1.001 |
          | W1  | place | houses | all     | 1 1, 1 1.001 |
        And the ways
          | id | nodes |
          | 1  | 1,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 1     | 3   | 1 1, 1 1.001 |

    Scenario: Even two point interpolation line with intermediate empty node
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 2       | 1 1 |
          | N2  | place | house  | 10      | 1.001 1.001 |
          | W1  | place | houses | even    | 1 1, 1 1.001, 1.001 1.001 |
        And the ways
          | id | nodes |
          | 1  | 1,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 10  | 1 1, 1 1.001, 1.001 1.001 |

    Scenario: Even two point interpolation line with intermediate duplicated empty node
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 2       | 1 1 |
          | N2  | place | house  | 10      | 1.001 1.001 |
          | W1  | place | houses | even    | 1 1, 1 1.001, 1.001 1.001 |
        And the ways
          | id | nodes |
          | 1  | 1,3,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 10  | 1 1, 1 1.001, 1.001 1.001 |

    Scenario: Simple even three point interpolation line
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  | 2       | 1 1 |
          | N2  | place | house  | 14      | 1.001 1.001 |
          | N3  | place | house  | 10      | 1 1.001 |
          | W1  | place | houses | even    | 1 1, 1 1.001, 1.001 1.001 |
        And the ways
          | id | nodes |
          | 1  | 1,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 10  | 1 1, 1 1.001 |
          | 10    | 14  | 1 1.001, 1.001 1.001 |

    Scenario: Simple even four point interpolation line
        Given the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 1 1 |
          | N2  | place | house | 14      | 1.001 1.001 |
          | N3  | place | house | 10      | 1 1.001 |
          | N4  | place | house | 18      | 1.001 1.002 |
          | W1  | place | houses | even    | 1 1, 1 1.001, 1.001 1.001, 1.001 1.002 |
        And the ways
          | id | nodes |
          | 1  | 1,3,2,4 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 10  | 1 1, 1 1.001 |
          | 10    | 14  | 1 1.001, 1.001 1.001 |
          | 14    | 18  | 1.001 1.001, 1.001 1.002 |

    Scenario: Reverse simple even three point interpolation line
        Given the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 1 1 |
          | N2  | place | house | 14      | 1.001 1.001 |
          | N3  | place | house | 10      | 1 1.001 |
          | W1  | place | houses | even    | 1.001 1.001, 1 1.001, 1 1 |
        And the ways
          | id | nodes |
          | 1  | 2,3,1 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 10  | 1 1, 1 1.001 |
          | 10    | 14  | 1 1.001, 1.001 1.001 |

    Scenario: Even three point interpolation line with odd center point
        Given the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 1 1 |
          | N2  | place | house | 8       | 1.001 1.001 |
          | N3  | place | house | 7       | 1 1.001 |
          | W1  | place | houses | even    | 1 1, 1 1.001, 1.001 1.001 |
        And the ways
          | id | nodes |
          | 1  | 1,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 7   | 1 1, 1 1.001 |
          | 7     | 8   | 1 1.001, 1.001 1.001 |

    Scenario: Interpolation line with self-intersecting way
        Given the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 0 0 |
          | N2  | place | house | 6       | 0 0.001 |
          | N3  | place | house | 10      | 0 0.002 |
          | W1  | place | houses | even    | 0 0, 0 0.001, 0 0.002, 0 0.001 |
        And the ways
          | id | nodes |
          | 1  | 1,2,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 6   | 0 0, 0 0.001 |
          | 6     | 10  | 0 0.001, 0 0.002 |
          | 6     | 10  | 0 0.001, 0 0.002 |

    Scenario: Interpolation line with self-intersecting way II
        Given the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | 0 0 |
          | N2  | place | house | 6       | 0 0.001 |
          | W1  | place | houses | even    | 0 0, 0 0.001, 0 0.002, 0 0.001 |
        And the ways
          | id | nodes |
          | 1  | 1,2,3,2 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 6   | 0 0, 0 0.001 |

    Scenario: addr:street on interpolation way
        Given the scene parallel-road
        And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-middle-w |
          | N2  | place | house | 6       | :n-middle-e |
          | N3  | place | house | 12      | :n-middle-w |
          | N4  | place | house | 16      | :n-middle-e |
        And the places
          | osm | class   | type    | housenr | street       | geometry |
          | W10 | place   | houses  | even    |              | :w-middle |
          | W11 | place   | houses  | even    | Cloud Street | :w-middle |
        And the places
          | osm | class   | type     | name         | geometry |
          | W2  | highway | tertiary | Sun Way      | :w-north |
          | W3  | highway | tertiary | Cloud Street | :w-south |
        And the ways
          | id | nodes |
          | 10  | 1,100,101,102,2 |
          | 11  | 3,200,201,202,4 |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
          | N3     | W3 |
          | N4     | W3 |
        Then W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |
        Then W11 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 12    | 16 |
        When searching for "16 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 4 |
        When searching for "14 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | W        | 11 |
        When searching for "18 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | W        | 3 |

    Scenario: addr:street on housenumber way
        Given the scene parallel-road
        And the places
          | osm | class | type  | housenr | street       | geometry |
          | N1  | place | house | 2       |              | :n-middle-w |
          | N2  | place | house | 6       |              | :n-middle-e |
          | N3  | place | house | 12      | Cloud Street | :n-middle-w |
          | N4  | place | house | 16      | Cloud Street | :n-middle-e |
        And the places
          | osm | class   | type    | housenr | geometry |
          | W10 | place   | houses  | even    | :w-middle |
          | W11 | place   | houses  | even    | :w-middle |
        And the places
          | osm | class   | type     | name         | geometry |
          | W2  | highway | tertiary | Sun Way      | :w-north |
          | W3  | highway | tertiary | Cloud Street | :w-south |
        And the ways
          | id  | nodes |
          | 10  | 1,100,101,102,2 |
          | 11  | 3,200,201,202,4 |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
          | N3     | W3 |
          | N4     | W3 |
        Then W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |
        Then W11 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 12    | 16 |
        When searching for "16 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 4 |
        When searching for "14 Cloud Street"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | W        | 11 |

    Scenario: Geometry of points and way don't match (github #253)
        Given the places
          | osm | class | type        | housenr | geometry |
          | N1  | place | house       | 10      | 144.9632341 -37.76163 |
          | N2  | place | house       | 6       | 144.9630541 -37.7628174 |
          | N3  | shop  | supermarket | 2       | 144.9629794 -37.7630755 |
          | W1  | place | houses      | even    | 144.9632341 -37.76163,144.9630541 -37.7628172,144.9629794 -37.7630755 |
        And the ways
          | id | nodes |
          | 1  | 1,2,3 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 2     | 6   | 144.9629794 -37.7630755, 144.9630541 -37.7628174 |
          | 6     | 10  | 144.9630541 -37.7628174, 144.9632341 -37.76163 |

    Scenario: Place with missing address information
        Given the places
          | osm | class   | type   | housenr | geometry |
          | N1  | place   | house  | 23      | 0.0001 0.0001 |
          | N2  | amenity | school |         | 0.0001 0.0002 |
          | N3  | place   | house  | 29      | 0.0001 0.0004 |
          | W1  | place   | houses | odd     | 0.0001 0.0001,0.0001 0.0002,0.0001 0.0004 |
        And the ways
          | id | nodes |
          | 1  | 1,2,3 |
        When importing
        Then W1 expands to interpolation
          | start | end | geometry |
          | 23    | 29  | 0.0001 0.0001, 0.0001 0.0002, 0.0001 0.0004 |

    Scenario: Ways without node entries are ignored
        Given the places
          | osm | class | type   | housenr | geometry |
          | W1  | place | houses | even    | 1 1, 1 1.001 |
        When importing
        Then W1 expands to no interpolation

    Scenario: Ways without nodes without housenumbers are ignored
        Given the places
          | osm | class | type   | housenr | geometry |
          | N1  | place | house  |         | 1 1 |
          | N2  | place | house  |         | 1 1.001 |
          | W1  | place | houses | even    | 1 1, 1 1.001 |
        When importing
        Then W1 expands to no interpolation


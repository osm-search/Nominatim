@DB
Feature: Import of address interpolations
    Tests that interpolated addresses are added correctly

    Scenario: Simple even two point interpolation
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | 1 1
          | 2      | place | house | 6           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 2           | 1,1
          | 4           | 1,1.0005
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 6           | 1,1.001

    Scenario: Simple even two point interpolation with zero beginning
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 0           | 1 1
          | 2      | place | house | 8           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 0           | 1,1
          | 2           | 1,1.00025
          | 4           | 1,1.0005
          | 6           | 1,1.00075
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 8           | 1,1.001

    Scenario: Backwards even two point interpolation
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | 1 1
          | 2      | place | house | 6           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1.001, 1 1
        And the ways
          | id | nodes
          | 1  | 2,1
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 2           | 1,1
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 4           | 1,1.0005
          | 6           | 1,1.001

    Scenario: Even two point interpolation with odd beginning
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 11          | 1 1
          | 2      | place | house | 16          | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 11          | 1,1
          | 12          | 1,1.0002
          | 14          | 1,1.0006
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 16          | 1,1.001

    Scenario: Even two point interpolation with odd end
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 10          | 1 1
          | 2      | place | house | 15          | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 10          | 1,1
          | 12          | 1,1.0004
          | 14          | 1,1.0008
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 15          | 1,1.001

    Scenario: Reverse even two point interpolation with odd beginning
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 11          | 1 1
          | 2      | place | house | 16          | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1.001, 1 1
        And the ways
          | id | nodes
          | 1  | 2,1
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 11          | 1,1
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 12          | 1,1.0002
          | 14          | 1,1.0006
          | 16          | 1,1.001

    Scenario: Reverse even two point interpolation with odd end
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 10          | 1 1
          | 2      | place | house | 15          | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1.001, 1 1
        And the ways
          | id | nodes
          | 1  | 2,1
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 10          | 1,1
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 12          | 1,1.0004
          | 14          | 1,1.0008
          | 15          | 1,1.001

      Scenario: Simple odd two point interpolation
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 1           | 1 1
          | 2      | place | house | 11          | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | odd         | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 1           | 1,1
          | 3           | 1,1.0002
          | 5           | 1,1.0004
          | 7           | 1,1.0006
          | 9           | 1,1.0008
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 11           | 1,1.001

      Scenario: Odd two point interpolation with even beginning
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | 1 1
          | 2      | place | house | 7           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | odd         | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 2           | 1,1
          | 3           | 1,1.0002
          | 5           | 1,1.0006
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 7           | 1,1.001

     Scenario: Simple all two point interpolation
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 1           | 1 1
          | 2      | place | house | 3           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | all         | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 1           | 1,1
          | 2           | 1,1.0005
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 3           | 1,1.001

    Scenario: Simple numbered two point interpolation
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 3           | 1 1
          | 2      | place | house | 9           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | 3           | 1 1, 1 1.001
        And the ways
          | id | nodes
          | 1  | 1,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 3           | 1,1
          | 6           | 1,1.0005
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 9           | 1,1.001

    Scenario: Even two point interpolation with intermediate empty node
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | 1 1
          | 2      | place | house | 10          | 1.001 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001, 1.001 1.001
        And the ways
          | id | nodes
          | 1  | 1,3,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 2           | 1,1
          | 4           | 1,1.0005
          | 6           | 1,1.001
          | 8           | 1.0005,1.001
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 10          | 1.001,1.001


    Scenario: Even two point interpolation with intermediate duplicated empty node
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | 1 1
          | 2      | place | house | 10          | 1.001 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001, 1.001 1.001
        And the ways
          | id | nodes
          | 1  | 1,3,3,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 2           | 1,1
          | 4           | 1,1.0005
          | 6           | 1,1.001
          | 8           | 1.0005,1.001
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 10          | 1.001,1.001

    Scenario: Simple even three point interpolation
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | 1 1
          | 2      | place | house | 8           | 1.001 1.001
          | 3      | place | house | 4           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001, 1.001 1.001
        And the ways
          | id | nodes
          | 1  | 1,3,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 2           | 1,1
        Then node 3 expands to housenumbers
          | housenumber | centroid
          | 4           | 1,1.001
          | 6           | 1.0005,1.001
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 8           | 1.001,1.001

    Scenario: Even three point interpolation with odd center point
        Given the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | 1 1
          | 2      | place | house | 8           | 1.001 1.001
          | 3      | place | house | 7           | 1 1.001
        And the place ways
          | osm_id | class | type   | housenumber | geometry
          | 1      | place | houses | even        | 1 1, 1 1.001, 1.001 1.001
        And the ways
          | id | nodes
          | 1  | 1,3,2
        When importing
        Then node 1 expands to housenumbers
          | housenumber | centroid
          | 2           | 1,1
          | 4           | 1,1.0004
          | 6           | 1,1.0008
        Then node 3 expands to housenumbers
          | housenumber | centroid
          | 7           | 1,1.001
        And node 2 expands to housenumbers
          | housenumber | centroid
          | 8           | 1.001,1.001



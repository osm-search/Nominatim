@DB
Feature: Update of address interpolations
    Test the interpolated address are updated correctly

    Scenario: new interpolation added to existing street
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 | 99 | 2 |    |
          |    |   |    |   |    |
          | 20 |   |    |   | 21 |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | 10,11    |
          | W3  | highway | unclassified | Cloud Street | 20,21    |
      And the ways
          | id  | nodes |
          | 10  | 1,2   |
      When importing
      Then W10 expands to no interpolation
      When updating places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And updating places
          | osm | class | type   | addr+interpolation | geometry |
          | W10 | place | houses | even               | 1,2      |
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end | geometry |
          | W2              | 4     | 4   | 99       |

    Scenario: addr:street added to interpolation
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
          |    |   |    |   |    |
          | 20 |   |    |   | 21 |
      And the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W10 | place | houses | even               | 1,2      |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | 10,11    |
          | W3  | highway | unclassified | Cloud Street | 20,21    |
      And the ways
          | id  | nodes |
          | 10  | 1,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4   |
      When updating places
          | osm | class   | type    | addr+interpolation | street       | geometry |
          | W10 | place   | houses  | even               | Cloud Street | 1,2      |
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 4     | 4   |

    Scenario: addr:street added to housenumbers
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
          |    |   |    |   |    |
          | 20 |   |    |   | 21 |
      And the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W10 | place | houses | even               | 1,2      |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | 10,11    |
          | W3  | highway | unclassified | Cloud Street | 20,21    |
      And the ways
          | id  | nodes |
          | 10  | 1,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4 |
      When updating places
          | osm | class | type  | street      | housenr |
          | N1  | place | house | Cloud Street| 2       |
          | N2  | place | house | Cloud Street| 6       |
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 4     | 4   |

    Scenario: interpolation tag removed
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
          |    |   |    |   |    |
          | 20 |   |    |   | 21 |
      And the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And the places
          | osm | class | type   | addr+interpolation | geometry |
          | W10 | place | houses | even               | 1,2      |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | 10,11    |
          | W3  | highway | unclassified | Cloud Street | 20,21    |
      And the ways
          | id  | nodes |
          | 10  | 1,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4   |
      When marking for delete W10
      Then W10 expands to no interpolation
      And placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |

    Scenario: referenced road added
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
          |    |   |    |   |    |
          | 20 |   |    |   | 21 |
      And the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And the places
          | osm | class   | type    | addr+interpolation | street      | geometry |
          | W10 | place   | houses  | even               | Cloud Street| 1,2      |
      And the places
          | osm | class   | type         | name     | geometry |
          | W2  | highway | unclassified | Sun Way  | 10,11    |
      And the ways
          | id  | nodes |
          | 10  | 1,2   |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4 |
      When updating places
          | osm | class   | type         | name         | geometry |
          | W3  | highway | unclassified | Cloud Street | 20,21    |
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 4     | 4   |

    Scenario: referenced road deleted
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
          |    |   |    |   |    |
          | 20 |   |    |   | 21 |
      And the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And the places
          | osm | class   | type    | addr+interpolation | street      | geometry |
          | W10 | place   | houses  | even               | Cloud Street| 1,2      |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | 10,11    |
          | W3  | highway | unclassified | Cloud Street | 20,21    |
      And the ways
          | id  | nodes |
          | 10  | 1,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 4     | 4   |
      When marking for delete W3
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4   |

    Scenario: building becomes interpolation
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
          |    | 4 |    | 3 |    |
      And the places
          | osm | class    | type  | housenr | geometry    |
          | W1  | place    | house | 3       | (1,2,3,4,1) |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Cloud Street | 10,11    |
      When importing
      Then placex contains
          | object | parent_place_id |
          | W1     | W2 |
      Given the ways
          | id  | nodes |
          | 1   | 1,2   |
      When updating places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And updating places
          | osm | class   | type    | addr+interpolation | street      | geometry |
          | W1  | place   | houses  | even               | Cloud Street| 1,2      |
      Then placex has no entry for W1
      And W1 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4   |

    Scenario: interpolation becomes building
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
          |    | 4 |    | 3 |    |
      And the places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Cloud Street | 10,11    |
      And the ways
          | id  | nodes |
          | 1   | 1,2 |
      And the places
          | osm | class   | type    | addr+interpolation | street      | geometry |
          | W1  | place   | houses  | even               | Cloud Street| 1,2      |
      When importing
      Then placex has no entry for W1
      And W1 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4   |
      When updating places
          | osm | class    | type  | housenr | geometry    |
          | W1  | place    | house | 3       | (1,2,3,4,1) |
      Then placex contains
          | object | parent_place_id |
          | W1     | W2 |
      And W1 expands to no interpolation

    Scenario: housenumbers added to interpolation
      Given the grid
          | 10 |   |    |   | 11 |
          |    | 1 |    | 2 |    |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Cloud Street | 10,11    |
      And the ways
          | id  | nodes |
          | 1   | 1,2 |
      And the places
          | osm | class   | type    | addr+interpolation | geometry |
          | W1  | place   | houses  | even               | 1,2 |
      When importing
      Then W1 expands to no interpolation
      When updating places
          | osm | class | type  | housenr |
          | N1  | place | house | 2       |
          | N2  | place | house | 6       |
      Then W1 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 4     | 4   |

    Scenario: housenumber added in middle of interpolation
      Given the grid
          | 1 |  |  |   |  | 2 |
          | 3 |  |  | 4 |  | 5 |
      And the places
          | osm | class   | type         | name         | geometry |
          | W1  | highway | unclassified | Cloud Street | 1, 2     |
      And the ways
          | id  | nodes |
          | 2   | 3,4,5 |
      And the places
          | osm | class   | type    | addr+interpolation | geometry |
          | W2  | place   | houses  | even    | 3,4,5    |
      And the places
          | osm | class | type  | housenr |
          | N3  | place | house | 2       |
          | N5  | place | house | 10      |
      When importing
      Then W2 expands to interpolation
          | parent_place_id | start | end |
          | W1              | 4     | 8  |
      When updating places
          | osm | class | type  | housenr |
          | N4  | place | house | 6       |
      Then W2 expands to interpolation
          | parent_place_id | start | end |
          | W1              | 4     | 4   |
          | W1              | 8     | 8   |

    @Fail
    Scenario: housenumber removed in middle of interpolation
      Given the grid
          | 1 |  |  |   |  | 2 |
          | 3 |  |  | 4 |  | 5 |
      And the places
          | osm | class   | type         | name         | geometry |
          | W1  | highway | unclassified | Cloud Street | 1, 2     |
      And the ways
          | id  | nodes |
          | 2   | 3,4,5 |
      And the places
          | osm | class   | type    | addr+interpolation | geometry |
          | W2  | place   | houses  | even    | 3,4,5    |
      And the places
          | osm | class | type  | housenr |
          | N3  | place | house | 2       |
          | N4  | place | house | 6       |
          | N5  | place | house | 10      |
      When importing
      Then W2 expands to interpolation
          | parent_place_id | start | end |
          | W1              | 4     | 4   |
          | W1              | 8     | 8   |
      When marking for delete N4
      Then W2 expands to interpolation
          | parent_place_id | start | end |
          | W1              | 4     | 8   |

    Scenario: Change the start housenumber
      Given the grid
          | 1 |  | 2 |
          | 3 |  | 4 |
      And the places
          | osm | class   | type         | name         | geometry |
          | W1  | highway | unclassified | Cloud Street | 1, 2     |
      And the ways
          | id  | nodes |
          | 2   | 3,4   |
      And the places
          | osm | class   | type    | addr+interpolation | geometry |
          | W2  | place   | houses  | even    | 3,4      |
      And the places
          | osm | class | type  | housenr |
          | N3  | place | house | 2       |
          | N4  | place | house | 6       |
      When importing
      Then W2 expands to interpolation
          | parent_place_id | start | end |
          | W1              | 4     | 4   |
      When updating places
          | osm | class | type  | housenr |
          | N4  | place | house | 8       |
      Then W2 expands to interpolation
          | parent_place_id | start | end |
          | W1              | 4     | 6   |

    Scenario: Legal interpolation type changed to illegal one
      Given the grid
          | 1 |  | 2 |
          | 3 |  | 4 |
      And the places
          | osm | class   | type         | name         | geometry |
          | W1  | highway | unclassified | Cloud Street | 1, 2     |
      And the ways
          | id  | nodes |
          | 2   | 3,4   |
      And the places
          | osm | class   | type    | addr+interpolation | geometry |
          | W2  | place   | houses  | even               | 3,4      |
      And the places
          | osm | class | type  | housenr |
          | N3  | place | house | 2       |
          | N4  | place | house | 6       |
      When importing
      Then W2 expands to interpolation
          | parent_place_id | start | end |
          | W1              | 4     | 4   |
      When updating places
          | osm | class   | type    | addr+interpolation | geometry |
          | W2  | place   | houses  | 12-2               | 3,4      |
      Then W2 expands to no interpolation


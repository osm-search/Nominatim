@DB
Feature: Update of address interpolations
    Test the interpolated address are updated correctly

    Scenario: addr:street added to interpolation
      Given the scene parallel-road
      And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-middle-w |
          | N2  | place | house | 6       | :n-middle-e |
          | W10 | place | houses | even   | :w-middle |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | :w-north |
          | W3  | highway | unclassified | Cloud Street | :w-south |
      And the ways
          | id  | nodes |
          | 10  | 1,100,101,102,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |
      When updating places
          | osm | class   | type    | housenr | street       | geometry |
          | W10 | place   | houses  | even    | Cloud Street | :w-middle |
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 2     | 6 |

    Scenario: addr:street added to housenumbers
      Given the scene parallel-road
      And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-middle-w |
          | N2  | place | house | 6       | :n-middle-e |
          | W10 | place | houses | even   | :w-middle |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | :w-north |
          | W3  | highway | unclassified | Cloud Street | :w-south |
      And the ways
          | id  | nodes |
          | 10  | 1,100,101,102,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |
      When updating places
          | osm | class | type  | street      | housenr | geometry |
          | N1  | place | house | Cloud Street| 2       | :n-middle-w |
          | N2  | place | house | Cloud Street| 6       | :n-middle-e |
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 2     | 6 |

    Scenario: interpolation tag removed
      Given the scene parallel-road
      And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-middle-w |
          | N2  | place | house | 6       | :n-middle-e |
          | W10 | place | houses | even   | :w-middle |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | :w-north |
          | W3  | highway | unclassified | Cloud Street | :w-south |
      And the ways
          | id  | nodes |
          | 10  | 1,100,101,102,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |
      When marking for delete W10
      Then W10 expands to no interpolation
      And placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |

    Scenario: referenced road added
      Given the scene parallel-road
      And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-middle-w |
          | N2  | place | house | 6       | :n-middle-e |
      And the places
          | osm | class   | type    | housenr | street      | geometry |
          | W10 | place   | houses  | even    | Cloud Street| :w-middle |
      And the places
          | osm | class   | type         | name     | geometry |
          | W2  | highway | unclassified | Sun Way  | :w-north |
      And the ways
          | id  | nodes |
          | 10  | 1,100,101,102,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |
      When updating places
          | osm | class   | type         | name         | geometry |
          | W3  | highway | unclassified | Cloud Street | :w-south |
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 2     | 6 |

    Scenario: referenced road deleted
      Given the scene parallel-road
      And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-middle-w |
          | N2  | place | house | 6       | :n-middle-e |
      And the places
          | osm | class   | type    | housenr | street      | geometry |
          | W10 | place   | houses  | even    | Cloud Street| :w-middle |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Sun Way      | :w-north |
          | W3  | highway | unclassified | Cloud Street | :w-south |
      And the ways
          | id  | nodes |
          | 10  | 1,100,101,102,2 |
      When importing
      Then placex contains
          | object | parent_place_id |
          | N1     | W3 |
          | N2     | W3 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W3              | 2     | 6 |
      When marking for delete W3
      Then placex contains
          | object | parent_place_id |
          | N1     | W2 |
          | N2     | W2 |
      And W10 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |

    Scenario: building becomes interpolation
      Given the scene building-with-parallel-streets
      And the places
          | osm | class    | type  | housenr | geometry |
          | W1  | place    | house | 3       | :w-building |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Cloud Street | :w-south |
      When importing
      Then placex contains
          | object | parent_place_id |
          | W1     | W2 |
      Given the ways
          | id  | nodes |
          | 1   | 1,100,101,102,2 |
      When updating places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-north-w |
          | N2  | place | house | 6       | :n-north-e |
      And updating places
          | osm | class   | type    | housenr | street      | geometry |
          | W1  | place   | houses  | even    | Cloud Street| :w-north |
      Then placex has no entry for W1
      And W1 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |

    Scenario: interpolation becomes building
      Given the scene building-with-parallel-streets
      And the places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-north-w |
          | N2  | place | house | 6       | :n-north-e |
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Cloud Street | :w-south |
      And the ways
          | id  | nodes |
          | 1   | 1,100,101,102,2 |
      And the places
          | osm | class   | type    | housenr | street      | geometry |
          | W1  | place   | houses  | even    | Cloud Street| :w-north |
      When importing
      Then placex has no entry for W1
      And W1 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |
      When updating places
          | osm | class    | type  | housenr | geometry |
          | W1  | place    | house | 3       | :w-building |
      Then placex contains
          | object | parent_place_id |
          | W1     | W2 |

    Scenario: housenumbers added to interpolation
      Given the scene building-with-parallel-streets
      And the places
          | osm | class   | type         | name         | geometry |
          | W2  | highway | unclassified | Cloud Street | :w-south |
      And the ways
          | id  | nodes |
          | 1   | 1,100,101,102,2 |
      And the places
          | osm | class   | type    | housenr | geometry |
          | W1  | place   | houses  | even    | :w-north |
      When importing
      Then W1 expands to no interpolation
      When updating places
          | osm | class | type  | housenr | geometry |
          | N1  | place | house | 2       | :n-north-w |
          | N2  | place | house | 6       | :n-north-e |
      And updating places
          | osm | class   | type    | housenr | street      | geometry |
          | W1  | place   | houses  | even    | Cloud Street| :w-north |
      Then W1 expands to interpolation
          | parent_place_id | start | end |
          | W2              | 2     | 6 |

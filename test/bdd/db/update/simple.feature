@DB
Feature: Update of simple objects
    Testing simple updating functionality

    Scenario: Do delete small boundary features
        Given the places
          | osm | class    | type           | admin | geometry |
          | R1  | boundary | administrative | 3     | poly-area:1.0 |
        When importing
        Then placex contains
          | object | rank_search |
          | R1     | 6 |
        When marking for delete R1
        Then placex has no entry for R1

    Scenario: Do not delete large boundary features
        Given the places
          | osm | class    | type           | admin | geometry |
          | R1  | boundary | administrative | 3     | poly-area:5.0 |
        When importing
        Then placex contains
          | object | rank_search |
          | R1     | 6 |
        When marking for delete R1
        Then placex contains 
          | object | rank_search |
          | R1     | 6 |

    Scenario: Do delete large features of low rank
        Given the named places
          | osm | class    | type          | geometry |
          | W1  | place    | house         | poly-area:5.0 |
          | R1  | boundary | national_park | poly-area:5.0 |
        When importing
        Then placex contains
          | object | rank_address |
          | R1     | 30 |
          | W1     | 30 |
        When marking for delete R1,W1
        Then placex has no entry for W1
        Then placex has no entry for R1

    Scenario: type mutation
        Given the places
          | osm | class | type | geometry |
          | N3  | shop  | toys | 1 -1 |
        When importing
        Then placex contains
          | object | class | type | centroid |
          | N3     | shop  | toys | 1 -1 |
        When updating places
          | osm | class | type    | geometry |
          | N3  | shop  | grocery | 1 -1 |
        Then placex contains
          | object | class | type    | centroid |
          | N3     | shop  | grocery | 1 -1 |

    Scenario: remove postcode place when house number is added
        Given the places
          | osm | class | type     | postcode | geometry |
          | N3  | place | postcode | 12345    | 1 -1 |
        When importing
        Then placex contains
          | object | class | type |
          | N3     | place | postcode |
        When updating places
          | osm | class | type  | postcode | housenr | geometry |
          | N3  | place | house | 12345    | 13      | 1 -1 |
        Then placex contains
          | object | class | type |
          | N3     | place | house |

    Scenario: remove boundary when changing from polygon to way
        Given the grid
          | 1 | 2 |
          | 3 | 4 |
        And the places
          | osm | class    | type           | name | admin | geometry        |
          | W1  | boundary | administrative | Haha | 5     | (1, 2, 4, 3, 1) |
        When importing
        Then placex contains
          | object |
          | W1 |
        When updating places
          | osm | class    | type           | name | admin | geometry   |
          | W1  | boundary | administrative | Haha | 5     | 1, 2, 4, 3 |
        Then placex has no entry for W1

     #895
     Scenario: update rank when boundary is downgraded from admin to historic
        Given the grid
          | 1 | 2 |
          | 3 | 4 |
        And the places
          | osm | class    | type           | name | admin | geometry        |
          | W1  | boundary | administrative | Haha | 5     | (1, 2, 4, 3, 1) |
        When importing
        Then placex contains
          | object | rank_address |
          | W1     | 10           |
        When updating places
          | osm | class    | type           | name | admin | geometry        |
          | W1  | boundary | historic       | Haha | 5     | (1, 2, 4, 3, 1) |
        Then placex contains
          | object | rank_address |
          | W1     | 30            |

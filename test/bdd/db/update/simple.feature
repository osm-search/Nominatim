@DB
Feature: Update of simple objects
    Testing simple updating functionality

    Scenario: Do delete small boundary features
        Given the 1.0 grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type           | admin | geometry |
          | R1  | boundary | administrative | 3     | (1,2,3,4,1) |
        When importing
        Then placex contains
          | object | rank_search |
          | R1     | 6 |
        When marking for delete R1
        Then placex has no entry for R1

    Scenario: Do not delete large boundary features
        Given the 2.0 grid
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type           | admin | geometry |
          | R1  | boundary | administrative | 3     | (1,2,3,4,1) |
        When importing
        Then placex contains
          | object | rank_search |
          | R1     | 6 |
        When marking for delete R1
        Then placex contains
          | object | rank_search |
          | R1     | 6 |

    Scenario: Do delete large features of low rank
        Given the 2.0 grid
          | 1 | 2 |
          | 4 | 3 |
        Given the named places
          | osm | class    | type        | geometry |
          | W1  | place    | house       | (1,2,3,4,1) |
          | R1  | natural  | wood        | (1,2,3,4,1) |
          | R2  | highway  | residential | (1,2,3,4,1) |
        When importing
        Then placex contains
          | object | rank_address |
          | R1     | 0 |
          | R2     | 26 |
          | W1     | 30 |
        When marking for delete R1,R2,W1
        Then placex has no entry for W1
        Then placex has no entry for R1
        Then placex has no entry for R2

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
          | N3  | place | postcode | 12345    | country:de |
        When importing
        Then placex has no entry for N3
        When updating places
          | osm | class | type  | postcode | housenr | geometry |
          | N3  | place | house | 12345    | 13      | country:de |
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
          | W1     | 0            |

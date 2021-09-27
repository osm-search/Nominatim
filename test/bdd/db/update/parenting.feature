@DB
Feature: Update parenting of objects

    Scenario: POI inside building inherits addr:street change
        Given the scene building-on-street-corner
        And the named places
         | osm | class   | type       | geometry |
         | N1  | amenity | bank       | :n-inner |
         | N2  | shop    | bakery     | :n-edge-NS |
         | N3  | shop    | supermarket| :n-edge-WE |
        And the places
         | osm | class    | type | street  | housenr | geometry |
         | W1  | building | yes  | nowhere | 3       | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        When importing
        Then placex contains
         | object | parent_place_id | housenumber |
         | W1     | W2              | 3 |
         | N1     | W3              | 3 |
         | N2     | W3              | 3 |
         | N3     | W2              | 3 |
        When updating places
         | osm | class    | type | street | addr_place | housenr | geometry    |
         | W1  | building | yes  | foo    | nowhere    | 3       | :w-building |
        And updating places
         | osm | class   | type       | name | geometry |
         | N3  | shop    | supermarket| well | :n-edge-WE |
        Then placex contains
         | object | parent_place_id | housenumber |
         | W1     | W3              | 3 |
         | N1     | W3              | 3 |
         | N2     | W3              | 3 |
         | N3     | W3              | 3 |


    Scenario: Housenumber is reparented when street gets name matching addr:street
        Given the grid
         | 1 |    |   | 2 |
         |   | 10 |   |   |
         |   |    |   |   |
         | 3 |    |   | 4 |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | A street | 1,2      |
         | W2  | highway | residential | B street | 3,4      |
        And the places
         | osm | class    | type | housenr | street   | geometry |
         | N1  | building | yes  | 3       | X street | 10       |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1              |
        When updating places
         | osm | class   | type        | name     | geometry |
         | W2  | highway | residential | X street | 3,4      |
        Then placex contains
         | object | parent_place_id |
         | N1     | W2              |


    Scenario: Housenumber is reparented when street looses name matching addr:street
        Given the grid
         | 1 |    |   | 2 |
         |   | 10 |   |   |
         |   |    |   |   |
         | 3 |    |   | 4 |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | A street | 1,2      |
         | W2  | highway | residential | X street | 3,4      |
        And the places
         | osm | class    | type | housenr | street   | geometry |
         | N1  | building | yes  | 3       | X street | 10       |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2              |
        When updating places
         | osm | class   | type        | name     | geometry |
         | W2  | highway | residential | B street | 3,4      |
        Then placex contains
         | object | parent_place_id |
         | N1     | W1              |


    Scenario: Housenumber is reparented when street gets name matching addr:street
        Given the grid
         | 1 |    |   | 2 |
         |   | 10 |   |   |
         |   |    |   |   |
         | 3 |    |   | 4 |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | A street | 1,2      |
         | W2  | highway | residential | B street | 3,4      |
        And the places
         | osm | class    | type | housenr | street   | geometry |
         | N1  | building | yes  | 3       | X street | 10       |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1              |
        When updating places
         | osm | class   | type        | name     | geometry |
         | W2  | highway | residential | X street | 3,4      |
        Then placex contains
         | object | parent_place_id |
         | N1     | W2              |


    # Invalidation of geometries currently disabled for addr:place matches.
    @Fail
    Scenario: Housenumber is reparented when place is renamed to matching addr:place
        Given the grid
         | 1 |    |   | 2 |
         |   | 10 | 4 |   |
         |   |    |   |   |
         |   |    | 5 |   |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | A street | 1,2      |
         | N5  | place   | village     | Bdorf    | 5        |
         | N4  | place   | village     | Other    | 4        |
        And the places
         | osm | class    | type | housenr | addr_place | geometry |
         | N1  | building | yes  | 3       | Cdorf      | 10       |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | N4              |
        When updating places
         | osm | class   | type        | name     | geometry |
         | N5  | place   | village     | Cdorf    | 5        |
        Then placex contains
         | object | parent_place_id |
         | N1     | N5              |


    Scenario: Housenumber is reparented when it looses a matching addr:place
        Given the grid
         | 1 |    |   | 2 |
         |   | 10 | 4 |   |
         |   |    |   |   |
         |   |    | 5 |   |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | A street | 1,2      |
         | N5  | place   | village     | Bdorf    | 5        |
         | N4  | place   | village     | Other    | 4        |
        And the places
         | osm | class    | type | housenr | addr_place | geometry |
         | N1  | building | yes  | 3       | Bdorf      | 10       |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | N5              |
        When updating places
         | osm | class   | type        | name     | geometry |
         | N5  | place   | village     | Cdorf    | 5        |
        Then placex contains
         | object | parent_place_id |
         | N1     | N4              |

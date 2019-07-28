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
         | osm | class    | type | addr_place | housenr | geometry |
         | W1  | building | yes  | nowhere    | 3       | :w-building |
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



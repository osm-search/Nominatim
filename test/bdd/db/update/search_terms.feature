@DB
Feature: Update of search terms
    Tests that search_name table is updated correctly

    Scenario: POI-inherited postcode remains when another POI is deleted
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | housenr | postcode | street   | geometry |
         | N1  | place | house | 1       | 12345    | North St |:p-S1 |
         | N2  | place | house | 2       |          | North St |:p-S2 |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | North St | :w-north |
        When importing
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |
        When marking for delete N2
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |

@DB
Feature: Creation of search terms
    Tests that search_name table is filled correctly

    Scenario: POIs without a name have no search entry
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | geometry |
         | N1  | place   | house       | :p-N1 |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | :w-north |
        When importing
        Then search_name has no entry for N1

    Scenario: Named POIs inherit address from parent
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name     | geometry |
         | N1  | place   | house       | foo      | :p-N1 |
         | W1  | highway | residential | the road | :w-north |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | foo         | the road |

    Scenario: Roads take over the postcode from attached houses
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | housenr | postcode | street   | geometry |
         | N1  | place | house | 1       | 12345    | North St | :p-S1 |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | North St | :w-north |
        When importing
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |


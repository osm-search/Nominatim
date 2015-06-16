@DB
Feature: Creation of search terms
    Tests that search_name table is filled correctly

    Scenario: POIs without a name have no search entry
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | geometry
         | 1      | place | house | :p-N1
        And the place ways
         | osm_id | class   | type        | geometry
         | 1      | highway | residential | :w-north
        When importing
        Then table search_name has no entry for N1


    Scenario: Named POIs inherit address from parent
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | name | geometry
         | 1      | place | house | foo  | :p-N1
        And the place ways
         | osm_id | class   | type        | name     | geometry
         | 1      | highway | residential | the road | :w-north
        When importing
        Then search_name table contains
         | place_id | name_vector | nameaddress_vector
         | N1       | foo         | the road

    Scenario: Roads take over the postcode from attached houses
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | housenumber | postcode | street   | geometry
         | 1      | place | house | 1           | 12345    | North St |:p-S1
        And the place ways
         | osm_id | class   | type        | name     | geometry
         | 1      | highway | residential | North St | :w-north
        When importing
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 12345


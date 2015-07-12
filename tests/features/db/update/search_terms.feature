@DB
Feature: Update of search terms
    Tests that search_name table is filled correctly

    Scenario: POI-inherited postcode remains when way type is changed
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
        When updating place ways
         | osm_id | class   | type         | name     | geometry
         | 1      | highway | unclassified | North St | :w-north
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 12345

    Scenario: POI-inherited postcode remains when way name is changed
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
        When updating place ways
         | osm_id | class   | type         | name     | geometry
         | 1      | highway | unclassified | South St | :w-north
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 12345

    Scenario: POI-inherited postcode remains when way geometry is changed
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
        When updating place ways
         | osm_id | class   | type         | name     | geometry
         | 1      | highway | unclassified | South St | :w-south
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 12345

    Scenario: POI-inherited postcode is added when POI postcode changes
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
        When updating place nodes
         | osm_id | class | type  | housenumber | postcode | street   | geometry
         | 1      | place | house | 1           | 54321    | North St |:p-S1
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 54321

    Scenario: POI-inherited postcode remains when POI geometry changes
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
        When updating place nodes
         | osm_id | class | type  | housenumber | postcode | street   | geometry
         | 1      | place | house | 1           | 12345    | North St |:p-S2
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 12345


    Scenario: POI-inherited postcode remains when another POI is deleted
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | housenumber | postcode | street   | geometry
         | 1      | place | house | 1           | 12345    | North St |:p-S1
         | 2      | place | house | 2           |          | North St |:p-S2
        And the place ways
         | osm_id | class   | type        | name     | geometry
         | 1      | highway | residential | North St | :w-north
        When importing
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 12345
        When marking for delete N2
        Then search_name table contains
         | place_id | nameaddress_vector
         | W1       | 12345

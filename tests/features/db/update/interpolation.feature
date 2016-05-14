@DB
Feature: Update of address interpolations
    Test the interpolated address are updated correctly

    Scenario: addr:street added to interpolation
      Given the scene parallel-road
      And the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | :n-middle-w
          | 2      | place | house | 6           | :n-middle-e
      And the place ways
          | osm_id | class   | type    | housenumber | geometry
          | 10     | place   | houses  | even        | :w-middle
      And the place ways
          | osm_id | class   | type         | name                    | geometry
          | 2      | highway | unclassified | 'name' : 'Sun Way'      | :w-north
          | 3      | highway | unclassified | 'name' : 'Cloud Street' | :w-south
      And the ways
          | id  | nodes
          | 10  | 1,100,101,102,2
      When importing
      Then table placex contains
          | object | parent_place_id
          | N1     | W2
          | N2     | W2
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W2              | 2           | 6
      When updating place ways
          | osm_id | class   | type    | housenumber | street       | geometry
          | 10     | place   | houses  | even        | Cloud Street | :w-middle
      Then table placex contains
          | object | parent_place_id
          | N1     | W3
          | N2     | W3
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W3              | 2           | 6

    Scenario: addr:street added to housenumbers
      Given the scene parallel-road
      And the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | :n-middle-w
          | 2      | place | house | 6           | :n-middle-e
      And the place ways
          | osm_id | class   | type    | housenumber | geometry
          | 10     | place   | houses  | even        | :w-middle
      And the place ways
          | osm_id | class   | type         | name                    | geometry
          | 2      | highway | unclassified | 'name' : 'Sun Way'      | :w-north
          | 3      | highway | unclassified | 'name' : 'Cloud Street' | :w-south
      And the ways
          | id  | nodes
          | 10  | 1,100,101,102,2
      When importing
      Then table placex contains
          | object | parent_place_id
          | N1     | W2
          | N2     | W2
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W2              | 2           | 6
      When updating place nodes
          | osm_id | class | type  | street      | housenumber | geometry
          | 1      | place | house | Cloud Street| 2           | :n-middle-w
          | 2      | place | house | Cloud Street| 6           | :n-middle-e
      Then table placex contains
          | object | parent_place_id
          | N1     | W3
          | N2     | W3
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W3              | 2           | 6


    Scenario: interpolation tag removed
      Given the scene parallel-road
      And the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | :n-middle-w
          | 2      | place | house | 6           | :n-middle-e
      And the place ways
          | osm_id | class   | type    | housenumber | geometry
          | 10     | place   | houses  | even        | :w-middle
      And the place ways
          | osm_id | class   | type         | name                    | geometry
          | 2      | highway | unclassified | 'name' : 'Sun Way'      | :w-north
          | 3      | highway | unclassified | 'name' : 'Cloud Street' | :w-south
      And the ways
          | id  | nodes
          | 10  | 1,100,101,102,2
      When importing
      Then table placex contains
          | object | parent_place_id
          | N1     | W2
          | N2     | W2
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W2              | 2           | 6
      When marking for delete W10
      Then table location_property_osmline has no entry for W10
      And table placex contains
          | object | parent_place_id
          | N1     | W2
          | N2     | W2


    Scenario: referenced road added
      Given the scene parallel-road
      And the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | :n-middle-w
          | 2      | place | house | 6           | :n-middle-e
      And the place ways
          | osm_id | class   | type    | housenumber | street      | geometry
          | 10     | place   | houses  | even        | Cloud Street| :w-middle
      And the place ways
          | osm_id | class   | type         | name                    | geometry
          | 2      | highway | unclassified | 'name' : 'Sun Way'      | :w-north
      And the ways
          | id  | nodes
          | 10  | 1,100,101,102,2
      When importing
      Then table placex contains
          | object | parent_place_id
          | N1     | W2
          | N2     | W2
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W2              | 2           | 6
      When updating place ways
          | osm_id | class   | type         | name                    | geometry
          | 3      | highway | unclassified | 'name' : 'Cloud Street' | :w-south
      Then table placex contains
          | object | parent_place_id
          | N1     | W3
          | N2     | W3
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W3              | 2           | 6


    Scenario: referenced road deleted
      Given the scene parallel-road
      And the place nodes
          | osm_id | class | type  | housenumber | geometry
          | 1      | place | house | 2           | :n-middle-w
          | 2      | place | house | 6           | :n-middle-e
      And the place ways
          | osm_id | class   | type    | housenumber | street      | geometry
          | 10     | place   | houses  | even        | Cloud Street| :w-middle
      And the place ways
          | osm_id | class   | type         | name                    | geometry
          | 2      | highway | unclassified | 'name' : 'Sun Way'      | :w-north
          | 3      | highway | unclassified | 'name' : 'Cloud Street' | :w-south
      And the ways
          | id  | nodes
          | 10  | 1,100,101,102,2
      When importing
      Then table placex contains
          | object | parent_place_id
          | N1     | W3
          | N2     | W3
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W3              | 2           | 6
      When marking for delete W3
      Then table placex contains
          | object | parent_place_id
          | N1     | W2
          | N2     | W2
      And table location_property_osmline contains
          | object | parent_place_id | startnumber | endnumber
          | W10    | W2              | 2           | 6

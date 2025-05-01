Feature: Searching linked places
    Tests that information from linked places can be searched correctly

    Scenario: Additional names from linked places are searchable
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 2 |    |
         | 13 |   | 12 |
        Given the places
         | osm  | class    | type           | admin | name  | geometry |
         | R13  | boundary | administrative | 6     | Garbo | (10,11,12,13,10) |
        Given the places
         | osm  | class    | type           | admin | name+name:it |
         | N2   | place    | hamlet         | 15    | Vario        |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13 |
        When geocoding "Vario"
         | namedetails |
         | 1 |
        Then all results contain
         | object | display_name | namedetails!dict |
         | R13    | Garbo | "name": "Garbo", "name:it": "Vario" |
        When geocoding "Vario"
         | accept-language |
         | it |
        Then all results contain
         | object | display_name |
         | R13    | Vario |


    Scenario: Differing names from linked places are searchable
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 2 |    |
         | 13 |   | 12 |
        Given the places
         | osm  | class    | type           | admin | name  | geometry |
         | R13  | boundary | administrative | 6     | Garbo | (10,11,12,13,10) |
        Given the places
         | osm  | class    | type           | admin | name  |
         | N2   | place    | hamlet         | 15    | Vario |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13 |
        When geocoding "Vario"
         | namedetails |
         | 1 |
        Then all results contain
         | object | display_name | namedetails!dict |
         | R13    | Garbo        | "name": "Garbo", "_place_name": "Vario" |
        When geocoding "Garbo"
        Then all results contain
         | object | display_name |
         | R13    | Garbo |

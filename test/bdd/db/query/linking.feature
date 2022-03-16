@DB
Feature: Searching linked places
    Tests that information from linked places can be searched correctly

    Scenario: Additional names from linked places are searchable
        Given the places
         | osm  | class    | type           | admin | name  | geometry |
         | R13  | boundary | administrative | 6     | Garbo | poly-area:0.1 |
        Given the places
         | osm  | class    | type           | admin | name+name:it | geometry |
         | N2   | place    | hamlet         | 15    | Vario        | 0.006 0.00001 |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13 |
        When sending search query "Vario"
        Then results contain
         | osm | display_name |
         | R13 | Garbo |
        When sending search query "Vario"
         | accept-language |
         | it |
        Then results contain
         | osm | display_name |
         | R13 | Vario |


    Scenario: Differing names from linked places are searchable
        Given the places
         | osm  | class    | type           | admin | name  | geometry |
         | R13  | boundary | administrative | 6     | Garbo | poly-area:0.1 |
        Given the places
         | osm  | class    | type           | admin | name  | geometry |
         | N2   | place    | hamlet         | 15    | Vario | 0.006 0.00001 |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13 |
        When sending search query "Vario"
        Then results contain
         | osm | display_name |
         | R13 | Garbo |
        When sending search query "Garbo"
        Then results contain
         | osm | display_name |
         | R13 | Garbo |

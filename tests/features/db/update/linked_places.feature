@DB
Feature: Updates of linked places
    Tests that linked places are correctly added and deleted.
    

    Scenario: Add linked place when linking relation is renamed
        Given the place nodes
            | osm_id | class | type | name | geometry
            | 1      | place | city | foo  | 0 0
        And the place areas
            | osm_type | osm_id | class    | type           | name | admin_level | geometry
            | R        | 1      | boundary | administrative | foo  | 8           | poly-area:0.1
        When importing
        And sending query "foo" with dups
        Then results contain
         | osm_type
         | R
        When updating place areas
         | osm_type | osm_id | class    | type           | name   | admin_level | geometry
         | R        | 1      | boundary | administrative | foobar | 8           | poly-area:0.1
        Then table placex contains
         | object | linked_place_id
         | N1     | None
        When updating place areas
         | osm_type | osm_id | class    | type           | name   | admin_level | geometry
        When sending query "foo" with dups
        Then results contain
         | osm_type
         | N

    Scenario: Add linked place when linking relation is removed
        Given the place nodes
            | osm_id | class | type | name | geometry
            | 1      | place | city | foo  | 0 0
        And the place areas
            | osm_type | osm_id | class    | type           | name | admin_level | geometry
            | R        | 1      | boundary | administrative | foo  | 8           | poly-area:0.1
        When importing
        And sending query "foo" with dups
        Then results contain
         | osm_type
         | R
        When marking for delete R1
        Then table placex contains
         | object | linked_place_id
         | N1     | None
        When updating place areas
         | osm_type | osm_id | class    | type           | name   | admin_level | geometry
        And sending query "foo" with dups
        Then results contain
         | osm_type
         | N

    Scenario: Remove linked place when linking relation is added
        Given the place nodes
            | osm_id | class | type | name | geometry
            | 1      | place | city | foo  | 0 0
        When importing
        And sending query "foo" with dups
        Then results contain
         | osm_type
         | N
        When updating place areas
         | osm_type | osm_id | class    | type           | name   | admin_level | geometry
         | R        | 1      | boundary | administrative | foo    | 8           | poly-area:0.1
        Then table placex contains
         | object | linked_place_id
         | N1     | R1
        When sending query "foo" with dups
        Then results contain
         | osm_type
         | R

    Scenario: Remove linked place when linking relation is renamed
        Given the place nodes
            | osm_id | class | type | name | geometry
            | 1      | place | city | foo  | 0 0
        And the place areas
         | osm_type | osm_id | class    | type           | name   | admin_level | geometry
         | R        | 1      | boundary | administrative | foobar | 8           | poly-area:0.1
        When importing
        And sending query "foo" with dups
        Then results contain
         | osm_type
         | N
        When updating place areas
         | osm_type | osm_id | class    | type           | name   | admin_level | geometry
         | R        | 1      | boundary | administrative | foo    | 8           | poly-area:0.1
        Then table placex contains
         | object | linked_place_id
         | N1     | R1
        When sending query "foo" with dups
        Then results contain
         | osm_type
         | R


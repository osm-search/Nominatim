@DB
Feature: Updates of linked places
    Tests that linked places are correctly added and deleted.

    Scenario: Add linked place when linking relation is renamed
        Given the places
            | osm | class | type | name | geometry |
            | N1  | place | city | foo  | 0 0 |
        And the places
            | osm | class    | type           | name | admin | geometry |
            | R1  | boundary | administrative | foo  | 8     | poly-area:0.1 |
        When importing
        And searching for "foo" with dups
        Then results contain
         | osm_type |
         | R |
        When updating places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foobar | 8     | poly-area:0.1 |
        Then placex contains
         | object | linked_place_id |
         | N1     | - |
        When searching for "foo" with dups
        Then results contain
         | osm_type |
         | N |

    Scenario: Add linked place when linking relation is removed
        Given the places
            | osm | class | type | name | geometry |
            | N1  | place | city | foo  | 0 0 |
        And the places
            | osm | class    | type           | name | admin | geometry |
            | R1  | boundary | administrative | foo  | 8     | poly-area:0.1 |
        When importing
        And searching for "foo" with dups
        Then results contain
         | osm_type |
         | R |
        When marking for delete R1
        Then placex contains
         | object | linked_place_id |
         | N1     | - |
        When searching for "foo" with dups
        Then results contain
         | osm_type |
         | N |

    Scenario: Remove linked place when linking relation is added
        Given the places
            | osm | class | type | name | geometry |
            | N1  | place | city | foo  | 0 0 |
        When importing
        And searching for "foo" with dups
        Then results contain
         | osm_type |
         | N |
        When updating places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foo    | 8     | poly-area:0.1 |
        Then placex contains
         | object | linked_place_id |
         | N1     | R1 |
        When searching for "foo" with dups
        Then results contain
         | osm_type |
         | R |

    Scenario: Remove linked place when linking relation is renamed
        Given the places
            | osm | class | type | name | geometry |
            | N1  | place | city | foo  | 0 0 |
        And the places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foobar | 8     | poly-area:0.1 |
        When importing
        And searching for "foo" with dups
        Then results contain
         | osm_type |
         | N |
        When updating places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foo    | 8     | poly-area:0.1 |
        Then placex contains
         | object | linked_place_id |
         | N1     | R1 |
        When searching for "foo" with dups
        Then results contain
         | osm_type |
         | R |


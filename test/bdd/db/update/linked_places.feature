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

    Scenario: Update linking relation when linkee name is updated
        Given the places
         | osm | class    | type           | name | admin | geometry |
         | R1  | boundary | administrative | rel  | 8     | poly-area:0.1 |
        And the places
         | osm | class    | type        | name+name:de | admin | geometry |
         | N3  | place    | city           | pnt  | 30    | 0.00001 0 |
        And the relations
         | id | members  |
         | 1  | N3:label |
        When importing
        Then placex contains
         | object | linked_place_id | name+name:de |
         | R1     | -               | pnt  |
         | N3     | R1              | pnt  |
        When updating places
         | osm | class    | type        | name+name:de | admin | geometry |
         | N3  | place    | city        | newname  | 30    | 0.00001 0 |
        Then placex contains
         | object | linked_place_id | name+name:de |
         | N3     | R1              | newname  |
         | R1     | -               | newname  |

    Scenario: Updating linkee extratags keeps linker's extratags
        Given the named places
         | osm | class    | type           | extra+wikidata | admin | geometry |
         | R1  | boundary | administrative | 34             | 8     | poly-area:0.1 |
        And the named places
         | osm | class    | type           | geometry |
         | N3  | place    | city           | 0.00001 0 |
        And the relations
         | id | members  |
         | 1  | N3:label |
        When importing
        Then placex contains
         | object | extratags |
         | R1     | 'wikidata' : '34', 'linked_place' : 'city' |
        When updating places
         | osm | class    | type        | name    | extra+oneway | admin | geometry |
         | N3  | place    | city        | newname | yes          | 30    | 0.00001 0 |
        Then placex contains
         | object | extratags |
         | R1     | 'wikidata' : '34', 'oneway' : 'yes', 'linked_place' : 'city' |


@DB
Feature: Updates of linked places
    Tests that linked places are correctly added and deleted.

    Scenario: Linking is kept when boundary is updated
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 1 |    |
         | 13 |   | 12 |
        Given the places
            | osm | class | type | name |
            | N1  | place | city | foo  |
        And the places
            | osm | class    | type           | name | admin | geometry |
            | R1  | boundary | administrative | foo  | 8     | (10,11,12,13,10) |
        When importing
        Then placex contains
         | object | linked_place_id |
         | N1     | R1 |
        When updating places
         | osm | class    | type           | name | name+name:de | admin | geometry |
         | R1  | boundary | administrative | foo  | Dingens      | 8     | (10,11,12,13,10) |
        Then placex contains
         | object | linked_place_id |
         | N1     | R1 |


    Scenario: Add linked place when linking relation is renamed
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 1 |    |
         | 13 |   | 12 |
        Given the places
            | osm | class | type | name |
            | N1  | place | city | foo  |
        And the places
            | osm | class    | type           | name | admin | geometry |
            | R1  | boundary | administrative | foo  | 8     | (10,11,12,13,10) |
        When importing
        Then placex contains
         | object | linked_place_id |
         | N1     | R1 |
        When sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | R |
        When updating places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foobar | 8     | (10,11,12,13,10) |
        Then placex contains
         | object | linked_place_id |
         | N1     | - |
        When sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | N |

    Scenario: Add linked place when linking relation is removed
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 1 |    |
         | 13 |   | 12 |
        Given the places
            | osm | class | type | name |
            | N1  | place | city | foo  |
        And the places
            | osm | class    | type           | name | admin | geometry |
            | R1  | boundary | administrative | foo  | 8     | (10,11,12,13,10) |
        When importing
        And sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | R |
        When marking for delete R1
        Then placex contains
         | object | linked_place_id |
         | N1     | - |
        When sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | N |

    Scenario: Remove linked place when linking relation is added
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 1 |    |
         | 13 |   | 12 |
        Given the places
            | osm | class | type | name |
            | N1  | place | city | foo  |
        When importing
        And sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | N |
        When updating places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foo    | 8     | (10,11,12,13,10) |
        Then placex contains
         | object | linked_place_id |
         | N1     | R1 |
        When sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | R |

    Scenario: Remove linked place when linking relation is renamed
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 1 |    |
         | 13 |   | 12 |
        Given the places
            | osm | class | type | name |
            | N1  | place | city | foo  |
        And the places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foobar | 8     | (10,11,12,13,10) |
        When importing
        And sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | N |
        When updating places
         | osm | class    | type           | name   | admin | geometry |
         | R1  | boundary | administrative | foo    | 8     | (10,11,12,13,10) |
        Then placex contains
         | object | linked_place_id |
         | N1     | R1 |
        When sending search query "foo"
         | dups |
         | 1    |
        Then results contain
         | osm_type |
         | R |

    Scenario: Update linking relation when linkee name is updated
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 3 |    |
         | 13 |   | 12 |
        Given the places
         | osm | class    | type           | name | admin | geometry |
         | R1  | boundary | administrative | rel  | 8     | (10,11,12,13,10) |
        And the places
         | osm | class    | type        | name+name:de |
         | N3  | place    | city        | pnt          |
        And the relations
         | id | members  |
         | 1  | N3:label |
        When importing
        Then placex contains
         | object | linked_place_id | name+_place_name:de |
         | R1     | -               | pnt  |
        And placex contains
         | object | linked_place_id | name+name:de |
         | N3     | R1              | pnt  |
        When updating places
         | osm | class    | type        | name+name:de |
         | N3  | place    | city        | newname      |
        Then placex contains
         | object | linked_place_id | name+name:de |
         | N3     | R1              | newname  |
        And placex contains
         | object | linked_place_id | name+_place_name:de |
         | R1     | -               | newname  |

    Scenario: Update linking relation when linkee name is deleted
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 3 |    |
         | 13 |   | 12 |
        Given the places
         | osm | class    | type           | name | admin | geometry |
         | R1  | boundary | administrative | rel  | 8     | (10,11,12,13,10) |
        And the places
         | osm | class    | type           | name |
         | N3  | place    | city           | pnt  |
        And the relations
         | id | members  |
         | 1  | N3:label |
        When importing
        Then placex contains
         | object | linked_place_id | name+_place_name | name+name |
         | R1     | -               | pnt              | rel       |
        And placex contains
         | object | linked_place_id | name+name |
         | N3     | R1              | pnt  |
        When sending search query "pnt"
        Then results contain
          | osm |
          | R1  |
        When updating places
         | osm | class    | type        | name+name:de |
         | N3  | place    | city        | depnt        |
        Then placex contains
         | object | linked_place_id | name+name:de |
         | N3     | R1              | depnt  |
        And placex contains
         | object | linked_place_id | name+_place_name:de | name+name |
         | R1     | -               | depnt               | rel       |
        When sending search query "pnt"
        Then exactly 0 results are returned

    Scenario: Updating linkee extratags keeps linker's extratags
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 3 |    |
         | 13 |   | 12 |
        Given the named places
         | osm | class    | type           | extra+wikidata | admin | geometry |
         | R1  | boundary | administrative | 34             | 8     | (10,11,12,13,10) |
        And the named places
         | osm | class    | type           |
         | N3  | place    | city           |
        And the relations
         | id | members  |
         | 1  | N3:label |
        When importing
        Then placex contains
         | object | extratags |
         | R1     | 'wikidata' : '34', 'linked_place' : 'city' |
        When updating places
         | osm | class    | type        | name    | extra+oneway |
         | N3  | place    | city        | newname | yes          |
        Then placex contains
         | object | extratags |
         | R1     | 'wikidata' : '34', 'oneway' : 'yes', 'linked_place' : 'city' |

    Scenario: Remove linked_place info when linkee is removed
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 1 |    |
         | 13 |   | 12 |
        Given the places
            | osm | class | type | name |
            | N1  | place | city | foo  |
        And the places
            | osm | class    | type           | name | admin | geometry |
            | R1  | boundary | administrative | foo  | 8     | (10,11,12,13,10) |
        When importing
        Then placex contains
            | object | extratags |
            | R1     | 'linked_place' : 'city' |
        When marking for delete N1
        Then placex contains
            | object | extratags |
            | R1     |  |

    Scenario: Update linked_place info when linkee type changes
        Given the 0.1 grid
         | 10 |   | 11 |
         |    | 1 |    |
         | 13 |   | 12 |
        Given the places
            | osm | class | type | name |
            | N1  | place | city | foo  |
        And the places
            | osm | class    | type           | name | admin | geometry |
            | R1  | boundary | administrative | foo  | 8     | (10,11,12,13,10) |
        When importing
        Then placex contains
            | object | extratags |
            | R1     | 'linked_place' : 'city' |
        When updating places
            | osm | class | type | name |
            | N1  | place | town | foo  |
        Then placex contains
            | object | extratags |
            | R1     | 'linked_place' : 'town' |


    Scenario: Keep linking and ranks when place type changes
        Given the grid
            | 1 |   |   | 2 |
            |   |   | 9 |   |
            | 4 |   |   | 3 |
        And the places
            | osm | class    | type           | name | admin | geometry    |
            | R1  | boundary | administrative | foo  | 8     | (1,2,3,4,1) |
        And the places
            | osm | class | type | name | geometry |
            | N1  | place | city | foo  | 9        |
        When importing
        Then placex contains
            | object | linked_place_id | rank_address |
            | N1     | R1              | 16           |
            | R1     | -               | 16           |

        When updating places
            | osm | class | type | name | geometry |
            | N1  | place | town | foo  | 9        |
        Then placex contains
            | object | linked_place_id | rank_address |
            | N1     | R1              | 16           |
            | R1     | -               | 16           |


    Scenario: Invalidate surrounding place nodes when place type changes
        Given the grid
            | 1 |   |   | 2 |
            |   | 8 | 9 |   |
            | 4 |   |   | 3 |
        And the places
            | osm | class    | type           | name | admin | geometry    |
            | R1  | boundary | administrative | foo  | 8     | (1,2,3,4,1) |
        And the places
            | osm | class | type | name | geometry |
            | N1  | place | town | foo  | 9        |
            | N2  | place | city | bar  | 8        |
        And the relations
         | id | members  |
         | 1  | N1:label |
        When importing
        Then placex contains
            | object | linked_place_id | rank_address |
            | N1     | R1              | 16           |
            | R1     | -               | 16           |
            | N2     | -               | 18           |

        When updating places
            | osm | class | type   | name | geometry |
            | N1  | place | suburb | foo  | 9        |
        Then placex contains
            | object | linked_place_id | rank_address |
            | N1     | R1              | 20           |
            | R1     | -               | 20           |
            | N2     | -               | 16           |

@DB
Feature: Linking of places
    Tests for correctly determining linked places

    Scenario: Only address-describing places can be linked
        Given the scene way-area-with-center
        And the places
         | osm  | class   | type   | name  | geometry |
         | R13  | landuse | forest | Garbo | :area |
         | N256 | natural | peak   | Garbo | :inner-C |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | R13     | - |
         | N256    | - |

    Scenario: Postcode areas cannot be linked
        Given the grid
         | 1 |   | 2 |
         |   | 9 |   |
         | 4 |   | 3 |
        And the named places
         | osm | class    | type        | addr+postcode  | extra+wikidata | geometry    |
         | R13 | boundary | postal_code | 123            | Q87493         | (1,2,3,4,1) |
         | N25 | place    | suburb      | 123            | Q87493         | 9 |
        When importing
        Then placex contains
         | object | linked_place_id |
         | R13    | - |
         | N25    | - |

     Scenario: Waterways are linked when in waterway relations
        Given the scene split-road
        And the places
         | osm | class    | type  | name  | geometry |
         | W1  | waterway | river | Rhein | :w-2 |
         | W2  | waterway | river | Rhein | :w-3 |
         | R13 | waterway | river | Rhein | :w-1 + :w-2 + :w-3 |
         | R23 | waterway | river | Limmat| :w-4a |
        And the relations
         | id | members                          | tags+type |
         | 13 | R23:tributary,W1,W2:main_stream  | waterway |
        When importing
        Then placex contains
         | object | linked_place_id |
         | W1     | R13 |
         | W2     | R13 |
         | R13    | -   |
         | R23    | -   |
        When searching for "rhein"
        Then results contain
         | osm_type |
         | R |

    Scenario: Relations are not linked when in waterway relations
        Given the scene split-road
        And the places
         | osm | class    | type   | name  | geometry |
         | W1  | waterway | stream | Rhein | :w-2 |
         | W2  | waterway | river  | Rhein | :w-3 |
         | R1  | waterway | river  | Rhein | :w-1 + :w-2 + :w-3 |
         | R2  | waterway | river  | Limmat| :w-4a |
        And the relations
         | id | members                          | tags+type |
         | 1  | R2                               | waterway  |
        When importing
        Then placex contains
         | object | linked_place_id |
         | W1     | - |
         | W2     | - |
         | R1     | - |
         | R2     | - |

    Scenario: Empty waterway relations are handled correctly
        Given the scene split-road
        And the places
         | osm | class    | type  | name  | geometry |
         | R1  | waterway | river | Rhein | :w-1 + :w-2 + :w-3 |
        And the relations
         | id | members  | tags+type |
         | 1  |          | waterway |
        When importing
        Then placex contains
         | object | linked_place_id |
         | R1     | - |

    Scenario: Waterways are not linked when the way type is not a river feature
        Given the scene split-road
        And the places
         | osm | class    | type     | name  | geometry |
         | W1  | waterway | lock     | Rhein | :w-2 |
         | R1  | waterway | river    | Rhein | :w-1 + :w-2 + :w-3 |
        And the relations
         | id | members               | tags+type |
         | 1  | N23,N34,W1,R45        | multipolygon |
        When importing
        Then placex contains
         | object | linked_place_id |
         | W1     | - |
         | R1     | - |
        When searching for "rhein"
        Then results contain
          | ID | osm_type |
          |  0 | R |
          |  1 | W |

    Scenario: Side streams are linked only when they have the same name
        Given the scene split-road
        And the places
         | osm | class    | type  | name   | geometry |
         | W1  | waterway | river | Rhein2 | :w-2 |
         | W2  | waterway | river | Rhein  | :w-3 |
         | R1  | waterway | river | Rhein  | :w-1 + :w-2 + :w-3 |
        And the relations
         | id | members                           | tags+type |
         | 1  | W1:side_stream,W2:side_stream     | waterway |
        When importing
        Then placex contains
         | object | linked_place_id |
         | W1     | -  |
         | W2     | R1 |
        When searching for "rhein2"
        Then results contain
         | osm_type |
         | W |

    # github #573
    Scenario: Boundaries should only be linked to places
        Given the named places
         | osm | class    | type           | extra+wikidata | admin | geometry |
         | R1  | boundary | administrative | 34             | 8     | poly-area:0.1 |
        And the named places
         | osm | class    | type           | geometry |
         | N3  | natural  | island         | 0.00001 0 |
         | N3  | place    | city           | 0.00001 0 |
        And the relations
         | id | members  |
         | 1  | N3:label |
        When importing
        Then placex contains
         | object     | linked_place_id |
         | N3:natural | -               |
         | N3:place   | R1              |

    Scenario: Nodes with 'role' label are always linked
        Given the places
         | osm  | class    | type           | admin | name  | geometry |
         | R13  | boundary | administrative | 6     | Garbo | poly-area:0.1 |
         | N2   | place    | hamlet         | 15    | Vario | 0.006 0.00001 |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13 |
        And placex contains
         | object | centroid      | name+name | extratags+linked_place |
         | R13    | 0.006 0.00001 | Garbo     | hamlet |

    Scenario: Boundaries with place tags are linked against places with same type
        Given the places
         | osm  | class    | type           | admin | name   | extra+place | geometry |
         | R13  | boundary | administrative | 4     | Berlin | city        |poly-area:0.1 |
        And the places
         | osm  | class    | type           | name   | geometry |
         | N2   | place    | city           | Berlin | 0.006 0.00001 |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13             |
        And placex contains
         | object | rank_address |
         | R13    | 16 |
        When searching for ""
         | city |
         | Berlin |
        Then results contain
          | ID | osm_type | osm_id |
          |  0 | R | 13 |
        When searching for ""
         | state |
         | Berlin |
        Then results contain
          | ID | osm_type | osm_id |
          |  0 | R | 13 |


    Scenario: Boundaries without place tags only link against same admin level
        Given the places
         | osm  | class    | type           | admin | name   | geometry |
         | R13  | boundary | administrative | 4     | Berlin |poly-area:0.1 |
        And the places
         | osm  | class    | type           | name   | geometry |
         | N2   | place    | city           | Berlin | 0.006 0.00001 |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | -               |
        And placex contains
         | object | rank_address |
         | R13    | 8 |
        When searching for ""
         | state |
         | Berlin |
        Then results contain
          | ID | osm_type | osm_id |
          |  0 | R | 13 |
        When searching for ""
         | city |
         | Berlin |
        Then results contain
          | ID | osm_type | osm_id |
          |  0 | N | 2 |

    # github #1352
    Scenario: Do not use linked centroid when it is outside the area
        Given the named places
         | osm  | class    | type           | admin | geometry |
         | R13  | boundary | administrative | 4     | poly-area:0.01 |
        And the named places
         | osm  | class    | type           | geometry |
         | N2   | place    | city           | 0.1 0.1 |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object | linked_place_id |
         | N2     | R13             |
        And placex contains
         | object | centroid |
         | R13    | in geometry  |

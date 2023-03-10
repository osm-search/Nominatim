@DB
Feature: Linking of places
    Tests for correctly determining linked places

    Scenario: Only address-describing places can be linked
        Given the grid
         | 1 |  |   |  | 2 |
         |   |  | 9 |  |   |
         | 4 |  |   |  | 3 |
        And the places
         | osm  | class   | type   | name  | geometry |
         | R13  | landuse | forest | Garbo | (1,2,3,4,1) |
         | N256 | natural | peak   | Garbo | 9 |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | R13     | - |
         | N256    | - |

    Scenario: Postcode areas cannot be linked
        Given the grid with origin US
         | 1 |   | 2 |
         |   | 9 |   |
         | 4 |   | 3 |
        And the named places
         | osm | class    | type        | addr+postcode  | extra+wikidata | geometry    |
         | R13 | boundary | postal_code | 12345          | Q87493         | (1,2,3,4,1) |
         | N25 | place    | suburb      | 12345          | Q87493         | 9 |
        When importing
        Then placex contains
         | object | linked_place_id |
         | R13    | - |
         | N25    | - |

     Scenario: Waterways are linked when in waterway relations
        Given the grid
         | 1 |  |   |  | 3 | 4  |  |   |  | 6 |
         |   |  | 2 |  |   | 10 |  | 5 |  |   |
         |   |  |   |  |   | 11 |  |   |  |   |
        And the places
         | osm | class    | type  | name  | geometry |
         | W1  | waterway | river | Rhein | 1,2,3    |
         | W2  | waterway | river | Rhein | 3,4,5    |
         | R13 | waterway | river | Rhein | 1,2,3,4,5,6 |
         | R23 | waterway | river | Limmat| 4,10,11  |
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
        When sending search query "rhein"
        Then results contain
         | osm |
         | R13 |

    Scenario: Relations are not linked when in waterway relations
        Given the grid
         | 1 |  |   |  | 3 | 4  |  |   |  | 6 |
         |   |  | 2 |  |   | 10 |  | 5 |  |   |
         |   |  |   |  |   | 11 |  |   |  |   |
        And the places
         | osm | class    | type   | name  | geometry |
         | W1  | waterway | stream | Rhein | 1,2,3,4 |
         | W2  | waterway | river  | Rhein | 4,5,6 |
         | R1  | waterway | river  | Rhein | 1,2,3,4 |
         | R2  | waterway | river  | Limmat| 4,10,11 |
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
        When sending search query "rhein"
        Then results contain
          | ID | osm |
          |  0 | R1  |
          |  1 | W2  |


    Scenario: Empty waterway relations are handled correctly
        Given the grid
         | 1 |  |   |  | 3 |
        And the places
         | osm | class    | type  | name  | geometry |
         | R1  | waterway | river | Rhein | 1,3 |
        And the relations
         | id | members  | tags+type |
         | 1  |          | waterway |
        When importing
        Then placex contains
         | object | linked_place_id |
         | R1     | - |

    Scenario: Waterways are not linked when the way type is not a river feature
        Given the grid
         | 1 |   | 2 |
         |   |   |   |
         | 3 |   | 4 |
        And the places
         | osm | class    | type     | name  | geometry |
         | W1  | waterway | lock     | Rhein | 3,4 |
         | R1  | landuse  | meadow   | Rhein | (3,1,2,4,3) |
        And the relations
         | id | members      | tags+type |
         | 1  | W1,W2        | multipolygon |
        When importing
        Then placex contains
         | object | linked_place_id |
         | W1     | - |
         | R1     | - |

    Scenario: Side streams are linked only when they have the same name
        Given the grid
         |   |  |   |   | 8 |   |   |  |
         | 1 |  | 2 | 3 |   | 4 | 5 | 6|
         |   |  |   |   |   | 9 |   |  |
        And the places
         | osm | class    | type  | name   | geometry |
         | W1  | waterway | river | Rhein2 | 2,8,4 |
         | W2  | waterway | river | Rhein  | 3,9,5 |
         | R1  | waterway | river | Rhein  | 1,2,3,4,5,6 |
        And the relations
         | id | members                           | tags+type |
         | 1  | W1:side_stream,W2:side_stream,W3  | waterway |
        When importing
        Then placex contains
         | object | linked_place_id |
         | W1     | -  |
         | W2     | R1 |
        When sending search query "rhein2"
        Then results contain
         | osm |
         | W1  |

    # github #573
    Scenario: Boundaries should only be linked to places
        Given the 0.05 grid
         | 1 |   | 2 |
         |   | 9 |   |
         | 4 |   | 3 |
        Given the named places
         | osm | class    | type           | extra+wikidata | admin | geometry    |
         | R1  | boundary | administrative | 34             | 8     | (1,2,3,4,1) |
        And the named places
         | osm | class    | type           |
         | N9  | natural  | island         |
         | N9  | place    | city           |
        And the relations
         | id | members  |
         | 1  | N9:label |
        When importing
        Then placex contains
         | object     | linked_place_id |
         | N9:natural | -               |
         | N9:place   | R1              |

    Scenario: Nodes with 'role' label are always linked
        Given the 0.05 grid
         | 1 |   | 2 |
         |   | 9 |   |
         | 4 |   | 3 |
        Given the places
         | osm  | class    | type           | admin | name  | geometry    |
         | R13  | boundary | administrative | 6     | Garbo | (1,2,3,4,1) |
         | N2   | place    | hamlet         | 15    | Vario | 9           |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13 |
        And placex contains
         | object | centroid | name+name | extratags+linked_place |
         | R13    | 9        | Garbo     | hamlet |

    Scenario: Boundaries with place tags are linked against places with same type
        Given the 0.01 grid
         | 1 |   | 2 |
         |   | 9 |   |
         | 4 |   | 3 |
        Given the places
         | osm  | class    | type           | admin | name   | extra+place | geometry    |
         | R13  | boundary | administrative | 4     | Berlin | city        | (1,2,3,4,1) |
        And the places
         | osm  | class    | type           | name   | geometry |
         | N2   | place    | city           | Berlin | 9 |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | R13             |
        And placex contains
         | object | rank_address |
         | R13    | 16 |
        When sending search query ""
         | city |
         | Berlin |
        Then results contain
          | ID | osm |
          |  0 | R13 |
        When sending search query ""
         | state |
         | Berlin |
        Then results contain
          | ID | osm |
          |  0 | R13 |


    Scenario: Boundaries without place tags only link against same admin level
        Given the 0.05 grid
         | 1 |   | 2 |
         |   | 9 |   |
         | 4 |   | 3 |
        Given the places
         | osm  | class    | type           | admin | name   | geometry |
         | R13  | boundary | administrative | 4     | Berlin | (1,2,3,4,1) |
        And the places
         | osm  | class    | type           | name   | geometry |
         | N2   | place    | city           | Berlin | 9 |
        When importing
        Then placex contains
         | object  | linked_place_id |
         | N2      | -               |
        And placex contains
         | object | rank_address |
         | R13    | 8 |
        When sending search query ""
         | state |
         | Berlin |
        Then results contain
          | ID | osm |
          |  0 | R13 |
        When sending search query ""
         | city |
         | Berlin |
        Then results contain
          | ID | osm |
          |  0 | N2  |

    # github #1352
    Scenario: Do not use linked centroid when it is outside the area
        Given the 0.05 grid
         | 1 |   | 2 |   |
         |   |   |   | 9 |
         | 4 |   | 3 |   |
        Given the named places
         | osm  | class    | type           | admin | geometry |
         | R13  | boundary | administrative | 4     | (1,2,3,4,1) |
        And the named places
         | osm  | class    | type           | geometry |
         | N2   | place    | city           | 9 |
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

    Scenario: Place nodes can only be linked once
        Given the 0.02 grid
         | 1 |   | 2 |   | 5 |
         |   | 9 |   |   |   |
         | 4 |   | 3 |   | 6 |
        Given the named places
         | osm  | class    | type | extra+wikidata | geometry |
         | N2   | place    | city | Q1234          | 9        |
        And the named places
         | osm  | class    | type           | extra+wikidata | admin | geometry        |
         | R1   | boundary | administrative | Q1234          | 8     | (1,2,5,6,3,4,1) |
         | R2   | boundary | administrative | Q1234          | 9     | (1,2,3,4,1)     |
        When importing
        Then placex contains
         | object | linked_place_id |
         | N2     | R1              |
        And placex contains
         | object | extratags                |
         | R1     | 'linked_place' : 'city', 'wikidata': 'Q1234'  |
         | R2     | 'wikidata': 'Q1234'                     |


@DB
Feature: Address computation
    Tests for filling of place_addressline

    Scenario: place nodes are added to the address when they are close enough
        Given the 0.002 grid
            | 2 |  |  |  |  |  | 1 |  | 3 |
        And the places
            | osm | class | type     | name      | geometry |
            | N1  | place | square   | Square    | 1 |
            | N2  | place | hamlet   | West Farm | 2 |
            | N3  | place | hamlet   | East Farm | 3 |
        When importing
        Then place_addressline contains
            | object | address | fromarea |
            | N1     | N3      | False |
        Then place_addressline doesn't contain
            | object | address |
            | N1     | N2      |
        When sending search query "Square"
        Then results contain
           | osm | display_name      |
           | N1  | Square, East Farm |

    Scenario: given two place nodes, the closer one wins for the address
        Given the grid
            | 2 |  |  | 1 |  | 3 |
        And the named places
            | osm | class | type     | geometry |
            | N1  | place | square   | 1 |
            | N2  | place | hamlet   | 2 |
            | N3  | place | hamlet   | 3 |
        When importing
        Then place_addressline contains
            | object | address | fromarea | isaddress |
            | N1     | N3      | False    | True |
            | N1     | N2      | False    | False |

    Scenario: boundaries around the place are added to the address
        Given the grid
            | 1 |    | 4 | | 7 | 10 |
            | 2 |    | 5 | | 8 | 11 |
            |   |    |   | |   |    |
            |   |    |   | |   |    |
            |   |    | 6 | | 9 |    |
            |   | 99 |   | |   |    |
            | 3 |    |   | |   | 12 |
        And the named places
            | osm | class    | type           | admin | geometry |
            | R1  | boundary | administrative | 3     | (1,2,3,12,11,10,7,8,9,6,5,4,1) |
            | R2  | boundary | administrative | 4     | (2,3,12,11,8,9,6,5,2) |
            | N1  | place    | square         | 15    | 99 |
        When importing
        Then place_addressline contains
            | object | address | isaddress |
            | N1     | R1      | True |
            | N1     | R2      | True |

    Scenario: with boundaries of same rank the one with the closer centroid is prefered
        Given the grid
            | 1 |   |   | 3 |  | 5 |
            |   | 9 |   |   |  |   |
            | 2 |   |   | 4 |  | 6 |
        And the named places
            | osm | class    | type           | admin | geometry |
            | R1  | boundary | administrative | 8     | (1,2,4,3,1) |
            | R2  | boundary | administrative | 8     | (1,2,6,5,1) |
            | N1  | place    | square         | 15    | 9 |
        When importing
        Then place_addressline contains
            | object | address | isaddress |
            | N1     | R1      | True |
            | N1     | R2      | False |

    Scenario: boundary areas are preferred over place nodes in the address
        Given the grid
            | 1 |   |   |   |   |   | 3 |
            |   | 5 |   |   |   |   |   |
            |   | 6 |   |   |   |   |   |
            | 2 |   |   |   |   |   | 4 |
        And the named places
            | osm | class    | type    | admin | geometry |
            | N1  | place    | square  | 15    | 5 |
            | N2  | place    | city    | 15    | 6 |
            | R1  | place    | city    | 8     | (1,2,4,3,1) |
        When importing
        Then place_addressline contains
            | object | address | isaddress | cached_rank_address |
            | N1     | R1      | True      | 16                  |
            | N1     | N2      | False     | 16                  |

    Scenario: place nodes outside a smaller ranked area are ignored
        Given the grid
            | 1 |   | 2 |   |
            |   | 7 |   | 9 |
            | 4 |   | 3 |   |
        And the named places
            | osm | class    | type    | admin | geometry |
            | N1  | place    | square  | 15    | 7 |
            | N2  | place    | city    | 15    | 9 |
            | R1  | place    | city    | 8     | (1,2,3,4,1) |
        When importing
        Then place_addressline contains
            | object | address | isaddress | cached_rank_address |
            | N1     | R1      | True      | 16                  |
        And place_addressline doesn't contain
            | object | address |
            | N1     | N2      |


    Scenario: place nodes close enough to smaller ranked place nodes are included
        Given the 0.002 grid
            | 2 |   | 3 | 1 |
        And the named places
            | osm | class | type     | geometry |
            | N1  | place | square   | 1 |
            | N2  | place | hamlet   | 2 |
            | N3  | place | quarter  | 3 |
        When importing
        Then place_addressline contains
            | object | address | fromarea | isaddress |
            | N1     | N2      | False    | True      |
            | N1     | N3      | False    | True      |


    Scenario: place nodes too far away from a smaller ranked place nodes are marked non-address
        Given the 0.002 grid
            | 2 |  |  | 1 |  | 3 |
        And the named places
            | osm | class | type     | geometry |
            | N1  | place | square   | 1 |
            | N2  | place | hamlet   | 2 |
            | N3  | place | quarter  | 3 |
        When importing
        Then place_addressline contains
            | object | address | fromarea | isaddress |
            | N1     | N2      | False    | True      |
            | N1     | N3      | False    | False     |


    # github #121
    Scenario: Roads crossing boundaries should contain both states
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   | 7 |   |   | 8 |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 7, 8     |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
            | W1     | W11     | 10                  |


    Scenario: Roads following a boundary should contain both states
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   |   | 8 | 7 |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 2, 7, 8  |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
            | W1     | W11     | 10                  |

    Scenario: Roads should not contain boundaries they touch in a end point
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   | 7 |   | 8 |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 7, 8     |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 8, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 8, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
        Then place_addressline doesn't contain
            | object | address |
            | W1     | W11     |

    Scenario: Roads should not contain boundaries they touch in a middle point
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   | 7 |   | 8 |   |   |
            | 4 |   | 9 | 5 |   | 6 |
        And the named places
            | osm | class   | type | geometry |
            | W1  | highway | road | 7, 8, 9     |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 8, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 8, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | W1     | W10     | 10                  |
        Then place_addressline doesn't contain
            | object | address |
            | W1     | W11     |

    Scenario: Locality points should contain all boundaries they touch
        Given the 0.001 grid
            | 1 |   |   | 2 |   | 3 |
            |   |   |   | 8 |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class | type     | geometry |
            | N1  | place | locality | 8        |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (1, 2, 8, 5, 4, 1) |
            | W11 | boundary | administrative | 5     | (2, 3, 6, 5, 8, 2) |
        When importing
        Then place_addressline contains
            | object | address | cached_rank_address |
            | N1     | W10     | 10                  |
            | N1     | W11     | 10                  |

    Scenario: Areas should not contain boundaries they touch
        Given the grid
            | 1 |   |   | 2 |   | 3 |
            |   |   |   |   |   |   |
            | 4 |   |   | 5 |   | 6 |
        And the named places
            | osm | class    | type           | geometry      |
            | W1  | landuse  | industrial     | (1, 2, 5, 4, 1) |
        And the named places
            | osm | class    | type           | admin | geometry      |
            | W10 | boundary | administrative | 5     | (2, 3, 6, 5, 2) |
        When importing
        Then place_addressline doesn't contain
            | object | address |
            | W1     | W10     |

    Scenario: buildings with only addr:postcodes do not appear in the address of a way
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
            | R4  | boundary | administrative | 10    | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        And the places
            | osm | class    | type        | addr+postcode | geometry |
            | W22 | place    | postcode    | 445023        | :building:w2N |
        When importing
        Then place_addressline doesn't contain
            | object | address  |
            | W93    | W22      |

    Scenario: postcode boundaries do appear in the address of a way
        Given the scene admin-areas
        And the named places
            | osm | class    | type           | admin | addr+postcode | geometry |
            | R1  | boundary | administrative | 6     | 112           | :b0      |
            | R34 | boundary | administrative | 8     | 112 DE        | :b1:E    |
        And the places
            | osm | class    | type        | addr+postcode | geometry |
            | R4  | boundary | postal_code | 112 DE 34     | :b2:N    |
        And the named places
            | osm | class    | type           | geometry |
            | W93 | highway  | residential    | :w2N     |
        And the places
            | osm | class    | type        | addr+postcode | geometry |
            | W22 | place    | postcode    | 445023        | :building:w2N |
        When importing
        Then place_addressline contains
            | object | address |
            | W93    | R4      |

    Scenario: squares do not appear in the address of a street
        Given the grid
            |   | 1 |   | 2 |   |
            | 8 |   |   |   | 9 |
            |   | 4 |   | 3 |   |
        And the named places
            | osm | class    | type           | geometry |
            | W1  | highway  | residential    | 8, 9     |
            | W2  | place    | square         | (1, 2, 3 ,4, 1) |
        When importing
        Then place_addressline doesn't contain
            | object | address |
            | W1     | W2      |

    Scenario: addr:* tags are honored even when a street is far away from the place
        Given the grid
            | 1 |   | 2 |   |   | 5 |
            |   |   |   | 8 | 9 |   |
            | 4 |   | 3 |   |   | 6 |
        And the places
            | osm | class    | type           | admin | name  | geometry    |
            | R1  | boundary | administrative | 8     | Left  | (1,2,3,4,1) |
            | R2  | boundary | administrative | 8     | Right | (2,3,6,5,2) |
        And the places
            | osm | class   | type    | addr+city | geometry |
            | W1  | highway | primary | Left      | 8,9      |
            | W2  | highway | primary | Right     | 8,9      |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R1      | True      |
           | W1     | R2      | False     |
           | W2     | R2      | True      |
        And place_addressline doesn't contain
           | object | address |
           | W2     | R1      |


    Scenario: addr:* tags are honored even when a POI is far away from the place
        Given the grid
            | 1 |   | 2 |   |   | 5 |
            |   |   |   | 8 | 9 |   |
            | 4 |   | 3 |   |   | 6 |
        And the places
            | osm | class    | type           | admin | name  | geometry    |
            | R1  | boundary | administrative | 8     | Left  | (1,2,3,4,1) |
            | R2  | boundary | administrative | 8     | Right | (2,3,6,5,2) |
        And the places
            | osm | class   | type    | name      | addr+city | geometry |
            | W1  | highway | primary | Wonderway | Right     | 8,9      |
            | N1  | amenity | cafe    | Bolder    | Left      | 9        |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R2      | True      |
           | N1     | R1      | True      |
        And place_addressline doesn't contain
           | object | address |
           | W1     | R1      |
        When sending search query "Bolder"
        Then results contain
           | osm | display_name            |
           | N1  | Bolder, Wonderway, Left |

    Scenario: addr:* tags do not produce addresslines when the parent has the address part
        Given the grid
            | 1 |   |   | 5 |
            |   | 8 | 9 |   |
            | 4 |   |   | 6 |
        And the places
            | osm | class    | type           | admin | name  | geometry    |
            | R1  | boundary | administrative | 8     | Outer | (1,5,6,4,1) |
        And the places
            | osm | class   | type    | name      | addr+city | geometry |
            | W1  | highway | primary | Wonderway | Outer     | 8,9      |
            | N1  | amenity | cafe    | Bolder    | Outer     | 9        |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R1      | True      |
        And place_addressline doesn't contain
           | object | address |
           | N1     | R1      |
        When sending search query "Bolder"
        Then results contain
           | osm | display_name             |
           | N1  | Bolder, Wonderway, Outer |

    Scenario: addr:* tags on outside do not produce addresslines when the parent has the address part
        Given the grid
            | 1 |   | 2 |   |   | 5 |
            |   |   |   | 8 | 9 |   |
            | 4 |   | 3 |   |   | 6 |
        And the places
            | osm | class    | type           | admin | name  | geometry    |
            | R1  | boundary | administrative | 8     | Left  | (1,2,3,4,1) |
            | R2  | boundary | administrative | 8     | Right | (2,3,6,5,2) |
        And the places
            | osm | class   | type    | name      | addr+city | geometry |
            | W1  | highway | primary | Wonderway | Left      | 8,9      |
            | N1  | amenity | cafe    | Bolder    | Left      | 9        |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R1      | True      |
           | W1     | R2      | False     |
        And place_addressline doesn't contain
           | object | address |
           | N1     | R1      |
        When sending search query "Bolder"
        Then results contain
           | osm | display_name            |
           | N1  | Bolder, Wonderway, Left |

    Scenario: POIs can correct address parts on the fly
        Given the grid
            | 1 |   |   |   |  2 |   | 5 |
            |   |   |   | 9 |    | 8 |   |
            | 4 |   |   |   |  3 |   | 6 |
        And the places
            | osm | class    | type           | admin | name  | geometry    |
            | R1  | boundary | administrative | 8     | Left  | (1,2,3,4,1) |
            | R2  | boundary | administrative | 8     | Right | (2,3,6,5,2) |
        And the places
            | osm | class   | type    | name      | geometry |
            | W1  | highway | primary | Wonderway | 2,3      |
            | N1  | amenity | cafe    | Bolder    | 9        |
            | N2  | amenity | cafe    | Leftside  | 8        |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R1      | False     |
           | W1     | R2      | True      |
        And place_addressline doesn't contain
           | object | address |
           | N1     | R1      |
           | N2     | R2      |
        When sending search query "Bolder"
        Then results contain
           | osm | display_name            |
           | N1  | Bolder, Wonderway, Left |
        When sending search query "Leftside"
        Then results contain
           | osm | display_name               |
           | N2  | Leftside, Wonderway, Right |

    Scenario: POIs can correct address parts on the fly (with partial unmatching address)
        Given the grid
            | 1 |   |   |   |  2 |   | 5 |
            |   |   |   | 9 |    | 8 |   |
            |   | 10| 11|   |    | 12|   |
            | 4 |   |   |   |  3 |   | 6 |
        And the places
            | osm | class    | type           | admin | name  | geometry    |
            | R1  | boundary | administrative | 8     | Left  | (1,2,3,4,1) |
            | R2  | boundary | administrative | 8     | Right | (2,3,6,5,2) |
        And the places
            | osm | class   | type    | name      | geometry |
            | W1  | highway | primary | Wonderway | 10,11,12 |
        And the places
            | osm | class   | type    | name      | addr+suburb | geometry |
            | N1  | amenity | cafe    | Bolder    | Boring      | 9        |
            | N2  | amenity | cafe    | Leftside  | Boring      | 8        |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R1      | True      |
           | W1     | R2      | False     |
        And place_addressline doesn't contain
           | object | address |
           | N1     | R1      |
           | N2     | R2      |
        When sending search query "Bolder"
        Then results contain
           | osm | display_name            |
           | N1  | Bolder, Wonderway, Left |
        When sending search query "Leftside"
        Then results contain
           | osm | display_name               |
           | N2  | Leftside, Wonderway, Right |


    Scenario: POIs can correct address parts on the fly (with partial matching address)
        Given the grid
            | 1 |   |   |   |  2 |   | 5 |
            |   |   |   | 9 |    | 8 |   |
            |   | 10| 11|   |    | 12|   |
            | 4 |   |   |   |  3 |   | 6 |
        And the places
            | osm | class    | type           | admin | name  | geometry    |
            | R1  | boundary | administrative | 8     | Left  | (1,2,3,4,1) |
            | R2  | boundary | administrative | 8     | Right | (2,3,6,5,2) |
        And the places
            | osm | class   | type    | name      | geometry |
            | W1  | highway | primary | Wonderway | 10,11,12 |
        And the places
            | osm | class   | type    | name      | addr+state | geometry |
            | N1  | amenity | cafe    | Bolder    | Left       | 9        |
            | N2  | amenity | cafe    | Leftside  | Left       | 8        |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R1      | True      |
           | W1     | R2      | False     |
        And place_addressline doesn't contain
           | object | address |
           | N1     | R1      |
           | N2     | R2      |
        When sending search query "Bolder"
        Then results contain
           | osm | display_name            |
           | N1  | Bolder, Wonderway, Left |
        When sending search query "Leftside"
        Then results contain
           | osm | display_name               |
           | N2  | Leftside, Wonderway, Left |

    Scenario: POIs can correct address parts on the fly (with area partially covering street)
        Given the grid
            | 1 |   | 2 |   |    |   | 5 |
            |   |   |   |   |    | 8 |   |
            |   | 10| 11|   |    |   | 12|
            | 4 |   | 3 |   |    |   | 7 |
            | 13|   |   |   |    |   | 6 |

        And the places
            | osm | class    | type           | admin | name    | geometry        |
            | R1  | boundary | administrative | 22    | Left    | (1,2,3,4,1)     |
            | R2  | boundary | administrative | 8     | Right   | (2,5,6,13,4,3,2)|
            | R3  | boundary | administrative | 22    | Super   | (2,3,7,5,2)     |
            | R4  | boundary | administrative | 8     | Boring  | (1,2,3,4,1)     |
        And the places
            | osm | class   | type        | name      | geometry |
            | W1  | highway | residential | Wonderway | 10,11,12 |
        And the places
            | osm | class    | type    | name      | geometry |
            | N1  | building | yes     | Bolder    | 8        |
        When importing
        Then place_addressline contains
           | object | address | isaddress |
           | W1     | R2      | True      |
           | W1     | R4      | False     |
        And place_addressline doesn't contain
           | object | address |
           | N1     | R1      |
           | N1     | R3      |
        When sending search query "Bolder"
        Then results contain
           | osm | display_name                      |
           | N1  | Bolder, Wonderway, Central, Right |

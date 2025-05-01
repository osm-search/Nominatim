Feature: Creation of search terms
    Tests that search_name table is filled correctly

    Scenario: Semicolon-separated names appear as separate full names
        Given the places
         | osm | class   | type | name+alt_name |
         | N1  | place   | city | New York; Big Apple |
         | N2  | place   | town | New York Big Apple |
        When importing
        And geocoding "New York Big Apple"
        Then result 0 contains
         | object |
         | N2     |

    Scenario: Comma-separated names appear as a single full name
        Given the places
         | osm | class   | type | name+name |
         | N1  | place   | city | New York, Big Apple |
         | N2  | place   | town | New York Big Apple |
        When importing
        And geocoding "New York Big Apple"
        Then result 0 contains
         | object |
         | N1     |

    Scenario: Name parts before brackets appear as full names
        Given the places
         | osm | class   | type | name+name |
         | N1  | place   | city | Halle (Saale) |
         | N2  | place   | town | Halle |
        When importing
        And geocoding "Halle"
        Then result 0 contains
         | object |
         | N1     |
        When geocoding "Halle (Saale)"
        Then the result set contains
         | object |
         | N1 |

    Scenario: Unknown addr: tags can be found for unnamed POIs
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        | housenr | addr+city |
         | N1  | place   | house       | 23      | Walltown  |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | 10,11    |
        When importing
        When geocoding "23 Rose Street, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |
        When geocoding "Walltown, Rose Street 23"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |
        When geocoding "Rose Street 23, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |

    Scenario: Searching for unknown addr: tags also works for multiple words
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        | housenr | addr+city        |
         | N1  | place   | house       | 23      | Little Big Town  |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | 10,11    |
        When importing
        When geocoding "23 Rose Street, Little Big Town"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |
        When geocoding "Rose Street 23, Little Big Town"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |
        When geocoding "Little big Town, Rose Street 23"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |

     Scenario: Unnamed POI can be found when it has known addr: tags
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        | housenr | addr+city |
         | N1  | place   | house       | 23      | Walltown  |
        And the places
         | osm | class   | type        | name+name   | addr+city | geometry |
         | W1  | highway | residential | Rose Street | Walltown  | 10,11    |
        When importing
        When geocoding "23 Rose Street, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |

    Scenario: Unnamed POIs inherit parent name when unknown addr:place is present
        Given the grid
         | 100 |    |   |   |    | 101 |
         |     |    | 1 |   |    |     |
         | 103 | 10 |   |   | 11 | 102 |
        And the places
         | osm | class   | type        | housenr | addr+place |
         | N1  | place   | house       | 23      | Walltown   |
        And the places
         | osm | class   | type        | name+name    | geometry |
         | W1  | highway | residential | Rose Street  | 10,11    |
         | R1  | place   | city        | Strange Town | (100,101,102,103,100) |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | R1              |
        When geocoding "23 Rose Street"
        Then all results contain
         | object | display_name |
         | W1     | Rose Street, Strange Town |
        When geocoding "23 Walltown, Strange Town"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Walltown, Strange Town |
        When geocoding "Walltown 23, Strange Town"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Walltown, Strange Town |
        When geocoding "Strange Town, Walltown 23"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Walltown, Strange Town |

    Scenario: Named POIs can be searched by housenumber when unknown addr:place is present
        Given the grid
         | 100 |    |   |   |    | 101 |
         |     |    | 1 |   |    |     |
         | 103 | 10 |   |   | 11 | 102 |
        And the places
         | osm | class   | type  | name       | housenr | addr+place |
         | N1  | place   | house | Blue house | 23      | Walltown   |
        And the places
         | osm | class   | type        | name+name    | geometry |
         | W1  | highway | residential | Rose Street  | 10,11 |
         | R1  | place   | city        | Strange Town | (100,101,102,103,100) |
        When importing
        When geocoding "23 Walltown, Strange Town"
        Then the result set contains
         | object | display_name |
         | N1     | Blue house, 23, Walltown, Strange Town |
        When geocoding "Walltown 23, Strange Town"
        Then the result set contains
         | object | display_name |
         | N1     | Blue house, 23, Walltown, Strange Town |
        When geocoding "Strange Town, Walltown 23"
        Then the result set contains
         | object | display_name |
         | N1     | Blue house, 23, Walltown, Strange Town |
        When geocoding "Strange Town, Walltown 23, Blue house"
        Then the result set contains
         | object | display_name |
         | N1     | Blue house, 23, Walltown, Strange Town |
        When geocoding "Strange Town, Walltown, Blue house"
        Then the result set contains
         | object | display_name |
         | N1     | Blue house, 23, Walltown, Strange Town |

    Scenario: Named POIs can be found when unknown multi-word addr:place is present
        Given the grid
         | 100 |    |   |   |    | 101 |
         |     |    | 1 |   |    |     |
         | 103 | 10 |   |   | 11 | 102 |
        And the places
         | osm | class   | type  | name       | housenr | addr+place |
         | N1  | place   | house | Blue house | 23      | Moon sun   |
        And the places
         | osm | class   | type        | name+name    | geometry |
         | W1  | highway | residential | Rose Street  | 10,11    |
         | R1  | place   | city        | Strange Town | (100,101,102,103,100) |
        When importing
        When geocoding "23 Moon Sun, Strange Town"
        Then the result set contains
         | object | display_name |
         | N1     | Blue house, 23, Moon sun, Strange Town |
        When geocoding "Blue house, Moon Sun, Strange Town"
        Then the result set contains
         | object | display_name |
         | N1     | Blue house, 23, Moon sun, Strange Town |

    Scenario: Unnamed POIs doesn't inherit parent name when addr:place is present only in parent address
        Given the grid
         | 100 |    |   |   |    | 101 |
         |     |    | 1 |   |    |     |
         | 103 | 10 |   |   | 11 | 102 |
        And the places
         | osm | class   | type        | housenr | addr+place |
         | N1  | place   | house       | 23      | Walltown   |
        And the places
         | osm | class   | type        | name+name    | addr+city | geometry |
         | W1  | highway | residential | Rose Street  | Walltown  | 10,11    |
         | R1  | place   | suburb      | Strange Town | Walltown  | (100,101,102,103,100) |
        When importing
        When geocoding "23 Rose Street, Walltown"
        Then all results contain
         | object | display_name |
         | W1     | Rose Street, Strange Town |
        When geocoding "23  Walltown"
        Then all results contain
         | object | display_name |
         | N1     | 23, Walltown, Strange Town |

    Scenario: Unnamed POIs does inherit parent name when unknown addr:place and addr:street is present
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type   | housenr | addr+place | addr+street |
         | N1  | place   | house  | 23      | Walltown   | Lily Street |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | 10,11    |
        When importing
        When geocoding "23 Rose Street"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |
        When geocoding "23 Lily Street"
        Then exactly 0 results are returned

    Scenario: An unknown addr:street is ignored
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type   | housenr |  addr+street |
         | N1  | place   | house  | 23      |  Lily Street |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | 10,11    |
        When importing
        When geocoding "23 Rose Street"
        Then the result set contains
         | object | display_name |
         | N1     | 23, Rose Street |
        When geocoding "23 Lily Street"
        Then exactly 0 results are returned

    Scenario: Named POIs can be found through unknown address tags
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        | name+name  | housenr | addr+city |
         | N1  | place   | house       | Green Moss | 26      | Walltown  |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | 10,11    |
        When importing
        When geocoding "Green Moss, Rose Street, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | Green Moss, 26, Rose Street |
        When geocoding "Green Moss, 26, Rose Street, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | Green Moss, 26, Rose Street |
        When geocoding "26, Rose Street, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | Green Moss, 26, Rose Street |
        When geocoding "Rose Street 26, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | Green Moss, 26, Rose Street |
        When geocoding "Walltown, Rose Street 26"
        Then the result set contains
         | object | display_name |
         | N1     | Green Moss, 26, Rose Street |

    Scenario: Named POI doesn't inherit parent name when addr:place is present only in parent address
        Given the grid
         | 100 |    |   |   |    | 101 |
         |     |    | 1 |   |    |     |
         | 103 | 10 |   |   | 11 | 102 |
        And the places
         | osm | class   | type        | name+name  | addr+place |
         | N1  | place   | house       | Green Moss | Walltown   |
        And the places
         | osm | class   | type        | name+name    | geometry |
         | W1  | highway | residential | Rose Street  | 10,11    |
         | R1  | place   | suburb      | Strange Town | (100,101,102,103,100) |
        When importing
        When geocoding "Green Moss, Rose Street, Walltown"
        Then exactly 0 results are returned
        When geocoding "Green Moss, Walltown"
        Then the result set contains
         | object | display_name |
         | N1     | Green Moss, Walltown, Strange Town |

    Scenario: Named POIs inherit address from parent
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        | name     | geometry |
         | N1  | place   | house       | foo      | 1        |
         | W1  | highway | residential | the road | 10,11    |
        When importing
        When geocoding "foo, the road"
        Then all results contain
         | object |
         | N1     |

    Scenario: Some addr: tags are added to address
        Given the grid
         |    | 2 | 3 |    |
         | 10 |   |   | 11 |
        And the places
         | osm | class   | type        | name     |
         | N2  | place   | city        | bonn     |
         | N3  | place   | suburb      | smalltown|
        And the places
         | osm | class   | type    | name    | addr+city | addr+municipality | addr+suburb | geometry |
         | W1  | highway | service | the end | bonn      | New York          | Smalltown   | 10,11    |
        When importing
        When geocoding "the end, new york, bonn, smalltown"
        Then all results contain
         | object |
         | W1     |

    Scenario: A known addr:* tag is added even if the name is unknown
        Given the grid
         | 10 | | | | 11 |
        And the places
         | osm | class   | type        | name | addr+city | geometry |
         | W1  | highway | residential | Road | Nandu     | 10,11    |
        When importing
        And geocoding "Road, Nandu"
        Then all results contain
         | object |
         | W1     |

    Scenario: a linked place does not show up in search name
        Given the 0.01 grid
         | 10 |   | 11 |
         |    | 2 |    |
         | 13 |   | 12 |
        Given the places
         | osm  | class    | type           | name | admin | geometry |
         | R13  | boundary | administrative | Roma | 9     | (10,11,12,13,10) |
        And the places
         | osm  | class    | type           | name |
         | N2   | place    | city           | Cite |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object | linked_place_id |
         | N2     | R13             |
        When geocoding "Cite"
        Then all results contain
         | object |
         | R13 |

    Scenario: a linked waterway does not show up in search name
        Given the grid
         | 1 | | 2 | | 3 |
        And the places
         | osm | class    | type  | name  | geometry |
         | W1  | waterway | river | Rhein | 1,2      |
         | W2  | waterway | river | Rhein | 2,3      |
         | R13 | waterway | river | Rhein | 1,2,3    |
        And the relations
         | id | members            | tags+type |
         | 13 | W1,W2:main_stream  | waterway |
        When importing
        Then placex contains
         | object | linked_place_id |
         | W1     | R13 |
         | W2     | R13 |
        When geocoding "Rhein"
        Then all results contain
         | object |
         | R13 |

@DB
Feature: Creation of search terms
    Tests that search_name table is filled correctly

    Scenario Outline: Comma- and semicolon separated names appear as full names
        Given the places
         | osm | class   | type | name+alt_name |
         | N1  | place   | city | New York<sep>Big Apple |
        When importing
        Then search_name contains
         | object | name_vector |
         | N1     | #New York, #Big Apple |

    Examples:
         | sep |
         | ,   |
         | ;   |

    Scenario Outline: Name parts before brackets appear as full names
        Given the places
         | osm | class   | type | name+name |
         | N1  | place   | city | Halle (Saale) |
        When importing
        Then search_name contains
         | object | name_vector |
         | N1     | #Halle Saale, #Halle |

    Scenario: Unnamed POIs have no search entry
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        |
         | N1  | place   | house       |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | 10,11    |
        When importing
        Then search_name has no entry for N1

    Scenario: Unnamed POI has a search entry when it has unknown addr: tags
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
        Then search_name contains
         | object | nameaddress_vector |
         | N1     | #Rose Street, Walltown |
        When sending search query "23 Rose Street, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |
        When sending search query "Walltown, Rose Street 23"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |
        When sending search query "Rose Street 23, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |

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
        Then search_name contains
         | object | nameaddress_vector |
         | N1     | #Rose Street, rose, Little, Big, Town |
        When sending search query "23 Rose Street, Little Big Town"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |
        When sending search query "Rose Street 23, Little Big Town"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |
        When sending search query "Little big Town, Rose Street 23"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |

     Scenario: Unnamed POI has no search entry when it has known addr: tags
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
        Then search_name has no entry for N1
        When sending search query "23 Rose Street, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |

    Scenario: Unnamed POI must have a house number to get a search entry
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type   | addr+city |
         | N1  | place   | house  | Walltown  |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | 10,11    |
        When importing
        Then search_name has no entry for N1

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
        When sending search query "23 Rose Street"
        Then exactly 1 results are returned
        And results contain
         | osm | display_name |
         | W1  | Rose Street, Strange Town |
        When sending search query "23 Walltown, Strange Town"
        Then results contain
         | osm | display_name |
         | N1  | 23, Walltown, Strange Town |
        When sending search query "Walltown 23, Strange Town"
        Then results contain
         | osm | display_name |
         | N1  | 23, Walltown, Strange Town |
        When sending search query "Strange Town, Walltown 23"
        Then results contain
         | osm | display_name |
         | N1  | 23, Walltown, Strange Town |

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
        When sending search query "23 Walltown, Strange Town"
        Then results contain
         | osm | display_name |
         | N1  | Blue house, 23, Walltown, Strange Town |
        When sending search query "Walltown 23, Strange Town"
        Then results contain
         | osm | display_name |
         | N1  | Blue house, 23, Walltown, Strange Town |
        When sending search query "Strange Town, Walltown 23"
        Then results contain
         | osm | display_name |
         | N1  | Blue house, 23, Walltown, Strange Town |
        When sending search query "Strange Town, Walltown 23, Blue house"
        Then results contain
         | osm | display_name |
         | N1  | Blue house, 23, Walltown, Strange Town |
        When sending search query "Strange Town, Walltown, Blue house"
        Then results contain
         | osm | display_name |
         | N1  | Blue house, 23, Walltown, Strange Town |

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
        When sending search query "23 Moon Sun, Strange Town"
        Then results contain
         | osm | display_name |
         | N1  | Blue house, 23, Moon sun, Strange Town |
        When sending search query "Blue house, Moon Sun, Strange Town"
        Then results contain
         | osm | display_name |
         | N1  | Blue house, 23, Moon sun, Strange Town |

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
        When sending search query "23 Rose Street, Walltown"
        Then exactly 1 result is returned
        And results contain
         | osm | display_name |
         | W1  | Rose Street, Strange Town |
        When sending search query "23  Walltown"
        Then exactly 1 result is returned
        And results contain
         | osm | display_name |
         | N1  | 23, Walltown, Strange Town |

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
        Then search_name has no entry for N1
        When sending search query "23 Rose Street"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |
        When sending search query "23 Lily Street"
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
        Then search_name has no entry for N1
        When sending search query "23 Rose Street"
        Then results contain
         | osm | display_name |
         | N1  | 23, Rose Street |
        When sending search query "23 Lily Street"
        Then exactly 0 results are returned

    Scenario: Named POIs get unknown address tags added in the search_name table
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
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | #Green Moss | #Rose Street, Walltown |
        When sending search query "Green Moss, Rose Street, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | Green Moss, 26, Rose Street |
        When sending search query "Green Moss, 26, Rose Street, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | Green Moss, 26, Rose Street |
        When sending search query "26, Rose Street, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | Green Moss, 26, Rose Street |
        When sending search query "Rose Street 26, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | Green Moss, 26, Rose Street |
        When sending search query "Walltown, Rose Street 26"
        Then results contain
         | osm | display_name |
         | N1  | Green Moss, 26, Rose Street |

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
        When sending search query "Green Moss, Rose Street, Walltown"
        Then exactly 0 result is returned
        When sending search query "Green Moss, Walltown"
        Then results contain
         | osm | display_name |
         | N1  | Green Moss, Walltown, Strange Town |

    Scenario: Named POIs inherit address from parent
        Given the grid
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        | name     | geometry |
         | N1  | place   | house       | foo      | 1        |
         | W1  | highway | residential | the road | 10,11    |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | foo         | #the road |

    Scenario: Some addr: tags are added to address
        Given the grid
         |    | 2 | 3 |    |
         | 10 |   |   | 11 |
        And the places
         | osm | class   | type        | name     |
         | N2  | place   | city        | bonn     |
         | N3  | place   | suburb      | smalltown|
        And the named places
         | osm | class   | type    | addr+city | addr+municipality | addr+suburb | geometry |
         | W1  | highway | service | bonn      | New York          | Smalltown   | 10,11    |
        When importing
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | bonn, new, york, smalltown |

    Scenario: A known addr:* tag is added even if the name is unknown
        Given the grid
         | 10 | | | | 11 |
        And the places
         | osm | class   | type        | name | addr+city | geometry |
         | W1  | highway | residential | Road | Nandu     | 10,11    |
        When importing
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | nandu |

    Scenario: addr:postcode is not added to the address terms
        Given the grid with origin DE
         |    | 1 |  |    |
         | 10 |   |  | 11 |
        And the places
         | osm | class   | type        | name+ref  |
         | N1  | place   | state       | 12345     |
        And the named places
         | osm | class   | type        | addr+postcode | geometry |
         | W1  | highway | residential | 12345         | 10,11    |
        When importing
        Then search_name contains not
         | object | nameaddress_vector |
         | W1     | 12345 |

    Scenario: a linked place does not show up in search name
        Given the 0.01 grid
         | 10 |   | 11 |
         |    | 2 |    |
         | 13 |   | 12 |
        Given the named places
         | osm  | class    | type           | admin | geometry |
         | R13  | boundary | administrative | 9     | (10,11,12,13,10) |
        And the named places
         | osm  | class    | type           |
         | N2   | place    | city           |
        And the relations
         | id | members       | tags+type |
         | 13 | N2:label      | boundary |
        When importing
        Then placex contains
         | object | linked_place_id |
         | N2     | R13             |
        And search_name has no entry for N2

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
        And search_name has no entry for W1
        And search_name has no entry for W2

@DB
Feature: Creation of search terms
    Tests that search_name table is filled correctly

    Scenario: POIs without a name have no search entry
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | geometry |
         | N1  | place   | house       | :p-N1 |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | :w-north |
        When importing
        Then search_name has no entry for N1

    Scenario: Named POIs inherit address from parent
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name     | geometry |
         | N1  | place   | house       | foo      | :p-N1 |
         | W1  | highway | residential | the road | :w-north |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | foo         | the road |

    Scenario: Some addr: tags are added to address when the name exists
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name     | geometry |
         | N1  | place   | state       | new york | 80 80 |
         | N2  | place   | city        | bonn     | 81 81 |
         | N3  | place   | suburb      | smalltown| 80 81 |
        And the named places
         | osm | class   | type    | addr+city | addr+state | addr+suburb | geometry |
         | W1  | highway | service | bonn      | New York   | Smalltown   | :w-north |
        When importing
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | bonn, new york, smalltown |

    Scenario: A known addr:* tag is not added if the name is unknown
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name | addr+city | geometry |
         | W1  | highway | residential | Road | Nandu     | :w-north |
        When importing
        Then search_name contains not
         | object | nameaddress_vector |
         | W1     | nandu |

    Scenario: addr:postcode is not added to the address terms
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name+ref  | geometry |
         | N1  | place   | state       | 12345     | 80 80 |
        And the named places
         | osm | class   | type        | addr+postcode | geometry |
         | W1  | highway | residential | 12345 | :w-north |
        When importing
        Then search_name contains not
         | object | nameaddress_vector |
         | W1     | 12345 |

    Scenario: is_in is split and added to the address search terms
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name     | geometry |
         | N1  | place   | state       | new york | 80 80 |
         | N2  | place   | city        | bonn     | 81 81 |
         | N3  | place   | suburb      | smalltown| 80 81 |
        And the named places
         | osm | class   | type    | addr+is_in                | geometry |
         | W1  | highway | service | bonn, New York, Smalltown | :w-north |
        When importing
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | bonn, new york, smalltown |

    Scenario: a linked place does not show up in search name
        Given the named places
         | osm  | class    | type           | admin | geometry |
         | R13  | boundary | administrative | 9     | poly-area:0.01 |
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
        And search_name has no entry for N2

    Scenario: a linked waterway does not show up in search name
        Given the scene split-road
        And the places
         | osm | class    | type  | name  | geometry |
         | W1  | waterway | river | Rhein | :w-2 |
         | W2  | waterway | river | Rhein | :w-3 |
         | R13 | waterway | river | Rhein | :w-1 + :w-2 + :w-3 |
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

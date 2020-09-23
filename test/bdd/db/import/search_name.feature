@DB
Feature: Creation of search terms
    Tests that search_name table is filled correctly

    Scenario: Unnamed POIs have no search entry
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | geometry |
         | N1  | place   | house       | :p-N1 |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | :w-north |
        When importing
        Then search_name has no entry for N1

    Scenario: Unnamed POI has a search entry when it has unknown addr: tags
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | housenr | addr+city | geometry |
         | N1  | place   | house       | 23      | Walltown  | :p-N1 |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | :w-north |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | #23         | Rose Street, Walltown |
        When searching for "23 Rose Street, Walltown"
        Then results contain
         | osm_type | osm_id |
         | N        | 1 |

    Scenario: Unnamed POI has no search entry when it has known addr: tags
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | housenr | addr+city | geometry |
         | N1  | place   | house       | 23      | Walltown  | :p-N1 |
        And the places
         | osm | class   | type        | name+name   | addr+city | geometry |
         | W1  | highway | residential | Rose Street | Walltown | :w-north |
        When importing
        Then search_name has no entry for N1
        When searching for "23 Rose Street, Walltown"
        Then results contain
         | osm_type | osm_id |
         | N        | 1 |

    Scenario: Unnamed POI must have a house number to get a search entry
        Given the scene roads-with-pois
        And the places
         | osm | class   | type   | addr+city | geometry |
         | N1  | place   | house  | Walltown  | :p-N1 |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | :w-north |
        When importing
        Then search_name has no entry for N1

    Scenario: Unnamed POIs doesn't inherit parent name when unknown addr:place is present
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | housenr | addr+place | geometry |
         | N1  | place   | house       | 23      | Walltown   | :p-N1 |
        And the places
         | osm | class   | type        | name+name    | geometry |
         | W1  | highway | residential | Rose Street  | :w-north |
         | N2  | place   | city        | Strange Town | :p-N1 |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | #23         | Walltown |
        When searching for "23 Rose Street"
        Then exactly 1 results are returned
        And results contain
         | osm_type | osm_id |
         | W        | 1 |
        When searching for "23 Walltown"
        Then results contain
         | osm_type | osm_id |
         | N        | 1 |

    Scenario: Unnamed POIs doesn't inherit parent name when addr:place is present only in parent address
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | housenr | addr+place | geometry |
         | N1  | place   | house       | 23      | Walltown   | :p-N1 |
        And the places
         | osm | class   | type        | name+name    | addr+city | geometry |
         | W1  | highway | residential | Rose Street  | Walltown  | :w-north |
         | N2  | place   | suburb      | Strange Town | Walltown  | :p-N1 |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | #23         | Walltown |
        When searching for "23 Rose Street, Walltown"
        Then exactly 1 result is returned
        And results contain
         | osm_type | osm_id |
         | W        | 1 |
        When searching for "23  Walltown"
        Then exactly 1 result is returned
        And results contain
         | osm_type | osm_id |
         | N        | 1 |

    Scenario: Unnamed POIs does inherit parent name when unknown addr:place and addr:street is present
        Given the scene roads-with-pois
        And the places
         | osm | class   | type   | housenr | addr+place | addr+street | geometry |
         | N1  | place   | house  | 23      | Walltown   | Lily Street | :p-N1 |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | :w-north |
        When importing
        Then search_name has no entry for N1
        When searching for "23 Rose Street"
        Then results contain
         | osm_type | osm_id |
         | N        | 1 |
        When searching for "23 Lily Street"
        Then exactly 0 results are returned

    Scenario: An unknown addr:street is ignored
        Given the scene roads-with-pois
        And the places
         | osm | class   | type   | housenr |  addr+street | geometry |
         | N1  | place   | house  | 23      |  Lily Street | :p-N1 |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | :w-north |
        When importing
        Then search_name has no entry for N1
        When searching for "23 Rose Street"
        Then results contain
         | osm_type | osm_id |
         | N        | 1 |
        When searching for "23 Lily Street"
        Then exactly 0 results are returned

    Scenario: Named POIs have unknown address tags added in the search_name table
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name+name  | addr+city | geometry |
         | N1  | place   | house       | Green Moss | Walltown  | :p-N1 |
        And the places
         | osm | class   | type        | name+name   | geometry |
         | W1  | highway | residential | Rose Street | :w-north |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | #Green Moss | Rose Street, Walltown |
        When searching for "Green Moss, Rose Street, Walltown"
        Then results contain
         | osm_type | osm_id |
         | N        | 1 |

    Scenario: Named POI doesn't inherit parent name when addr:place is present only in parent address
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name+name  | addr+place | geometry |
         | N1  | place   | house       | Green Moss | Walltown  | :p-N1 |
        And the places
         | osm | class   | type        | name+name    | geometry |
         | W1  | highway | residential | Rose Street  | :w-north |
         | N2  | place   | suburb      | Strange Town | :p-N1 |
        When importing
        Then search_name contains
         | object | name_vector | nameaddress_vector |
         | N1     | #Green Moss | Walltown |
        When searching for "Green Moss, Rose Street, Walltown"
        Then exactly 0 result is returned
        When searching for "Green Moss, Walltown"
        Then results contain
         | osm_type | osm_id |
         | N        | 1 |

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

    Scenario: A known addr:* tag is added even if the name is unknown
        Given the scene roads-with-pois
        And the places
         | osm | class   | type        | name | addr+city | geometry |
         | W1  | highway | residential | Road | Nandu     | :w-north |
        When importing
        Then search_name contains
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

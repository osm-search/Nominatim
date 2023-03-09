@DB
Feature: Parenting of objects
    Tests that the correct parent is chosen

    Scenario: Address inherits postcode from its street unless it has a postcode
        Given the grid with origin DE
         | 10 |   |   |   |   | 11 |
         |    |   |   |   |   |    |
         |    | 1 |   | 2 |   |    |
        And the places
         | osm | class | type  | housenr |
         | N1  | place | house | 4       |
        And the places
         | osm | class | type  | housenr | postcode |
         | N2  | place | house | 5       | 99999    |
        And the places
         | osm | class   | type        | name  | postcode | geometry |
         | W1  | highway | residential | galoo | 12345    | 10,11    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
        When sending search query "4 galoo"
        Then results contain
         | ID | osm | display_name |
         | 0  | N1  | 4, galoo, 12345, Deutschland |
        When sending search query "5 galoo"
        Then results contain
         | ID | osm | display_name |
         | 0  | N2  | 5, galoo, 99999, Deutschland |

    Scenario: Address without tags, closest street
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 1 | 2 |   |   |    |
         |    |   |   | 3 | 4 |    |
         | 20 |   |   |   |   | 21 |
        And the places
         | osm | class | type  |
         | N1  | place | house |
         | N2  | place | house |
         | N3  | place | house |
         | N4  | place | house |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | 10,11    |
         | W2  | highway | residential | 20,21    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W2 |

    Scenario: Address without tags avoids unnamed streets
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 1 | 2 |   |   |    |
         |    |   |   | 3 | 4 |    |
         | 20 |   |   |   |   | 21 |
        And the places
         | osm | class   | type  |
         | N1  | place   | house |
         | N2  | place   | house |
         | N3  | place   | house |
         | N4  | place   | house |
        And the places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | 10,11    |
        And the named places
         | osm | class   | type        | geometry |
         | W2  | highway | residential | 20,21 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |
         | N2     | W2 |
         | N3     | W2 |
         | N4     | W2 |

    Scenario: addr:street tag parents to appropriately named street
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 1 | 2 |   |   |    |
         |    |   |   | 3 | 4 |    |
         | 20 |   |   |   |   | 21 |
        And the places
         | osm | class | type  | street|
         | N1  | place | house | south |
         | N2  | place | house | north |
         | N3  | place | house | south |
         | N4  | place | house | north |
        And the places
         | osm | class   | type        | name  | geometry |
         | W1  | highway | residential | north | 10,11    |
         | W2  | highway | residential | south | 20,21    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W1 |

    @fail-legacy
    Scenario: addr:street tag parents to appropriately named street, locale names
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 1 | 2 |   |   |    |
         |    |   |   | 3 | 4 |    |
         | 20 |   |   |   |   | 21 |
        And the places
         | osm | class | type  | street| addr+street:de |
         | N1  | place | house | south | Süd            |
         | N2  | place | house | north | Nord           |
         | N3  | place | house | south | Süd            |
         | N4  | place | house | north | Nord           |
        And the places
         | osm | class   | type        | name  | geometry |
         | W1  | highway | residential | Nord  | 10,11    |
         | W2  | highway | residential | Süd   | 20,21    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W1 |

    Scenario: addr:street tag parents to appropriately named street with abbreviation
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 1 | 2 |   |   |    |
         |    |   |   | 3 | 4 |    |
         | 20 |   |   |   |   | 21 |
        And the places
         | osm | class | type  | street   |
         | N1  | place | house | south st |
         | N2  | place | house | north st |
         | N3  | place | house | south st |
         | N4  | place | house | north st |
        And the places
         | osm | class   | type        | name+name:en | geometry |
         | W1  | highway | residential | north street | 10,11    |
         | W2  | highway | residential | south street | 20,21    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W1 |

    Scenario: addr:street tag parents to next named street
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 1 | 2 |   |   |    |
         |    |   |   | 3 | 4 |    |
         | 20 |   |   |   |   | 21 |
        And the places
         | osm | class | type  | street |
         | N1  | place | house | abcdef |
         | N2  | place | house | abcdef |
         | N3  | place | house | abcdef |
         | N4  | place | house | abcdef |
        And the places
         | osm | class   | type        | name   | geometry |
         | W1  | highway | residential | abcdef | 10,11    |
         | W2  | highway | residential | abcdef | 20,21    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W2 |

    Scenario: addr:street tag without appropriately named street
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 1 |   |   |   |    |
         |    |   |   | 3 |   |    |
         | 20 |   |   |   |   | 21 |
        And the places
         | osm | class | type  | street |
         | N1  | place | house | abcdef |
         | N3  | place | house | abcdef |
        And the places
         | osm | class   | type        | name  | geometry |
         | W1  | highway | residential | abcde | 10,11    |
         | W2  | highway | residential | abcde | 20,21    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N3     | W2 |

    Scenario: addr:place address
        Given the grid
         | 10 |   | |   |
         |    | 1 | | 2 |
         | 11 |   | |   |
        And the places
         | osm | class | type   | addr_place |
         | N1  | place | house  | myhamlet   |
        And the places
         | osm | class   | type        | name     | geometry |
         | N2  | place   | hamlet      | myhamlet | 2 |
         | W1  | highway | residential | myhamlet | 10,11 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | N2 |

    Scenario: addr:street is preferred over addr:place
        Given the grid
         | 10 |  |   |   |
         |    |  | 1 | 2 |
         | 11 |  |   |   |
        And the places
         | osm | class | type   | addr_place | street  |
         | N1  | place | house  | myhamlet   | mystreet|
        And the places
         | osm | class   | type        | name     | geometry |
         | N2  | place   | hamlet      | myhamlet | 2        |
         | W1  | highway | residential | mystreet | 10,11    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |

    Scenario: Untagged address in simple associated street relation
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 2 |   | 3 |   |    |
         |    |   |   |   |   |    |
         | 12 | 1 |   |   |   |    |
        And the places
         | osm | class | type  |
         | N1  | place | house |
         | N2  | place | house |
         | N3  | place | house |
        And the places
         | osm | class   | type        | name | geometry |
         | W1  | highway | residential | foo  | 10,11 |
         | W2  | highway | service     | bar  | 10,12 |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:street,N1,N2,N3 | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
         | N3     | W1 |

    Scenario: Avoid unnamed streets in simple associated street relation
        Given the grid
         | 10 |   |   |   |   | 11 |
         |    | 2 |   | 3 |   |    |
         |    |   |   |   |   |    |
         | 12 | 1 |   |   |   |    |
        And the places
         | osm | class | type  |
         | N1  | place | house |
         | N2  | place | house |
         | N3  | place | house |
        And the places
         | osm | class   | type        | geometry |
         | W2  | highway | residential | 10,12    |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | 10,11    |
        And the relations
         | id | members                      | tags+type |
         | 1  | N1,N2,N3,W2:street,W1:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
         | N3     | W1 |

    Scenario: Associated street relation overrides addr:street
        Given the grid
         | 10 |    |   |    | 11 |
         |    |    |   |    |    |
         |    |    | 1 |    |    |
         |    | 20 |   | 21 |    |
        And the places
         | osm | class | type  | street |
         | N1  | place | house | bar    |
        And the places
         | osm | class   | type        | name | geometry |
         | W1  | highway | residential | foo  | 10,11    |
         | W2  | highway | residential | bar  | 20,21    |
        And the relations
         | id | members      | tags+type |
         | 1  | W1:street,N1 | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |

    Scenario: Building without tags, closest street from center point
        Given the grid
         | 10 |  |   |   | 11 |
         |    |  | 1 | 2 |    |
         | 12 |  | 4 | 3 |    |
        And the named places
         | osm | class    | type        | geometry    |
         | W1  | building | yes         | (1,2,3,4,1) |
         | W2  | highway  | primary     | 10,11       |
         | W3  | highway  | residential | 10,12       |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W2 |

    Scenario: Building with addr:street tags
        Given the grid
         | 10 |  |   |   | 11 |
         |    |  | 1 | 2 |    |
         | 12 |  | 4 | 3 |    |
        And the named places
         | osm | class    | type | street | geometry |
         | W1  | building | yes  | foo    | (1,2,3,4,1) |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | 10,11    |
         | W3  | highway  | residential | foo  | 10,12    |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W3 |

    Scenario: Building with addr:place tags
        Given the grid
         | 10 |   |   |   |   |
         |    | 1 | 2 |   | 9 |
         | 11 | 4 | 3 |   |   |
        And the places
         | osm | class    | type        | name | geometry |
         | N9  | place    | village     | bar  | 9        |
         | W2  | highway  | primary     | bar  | 10,11    |
        And the named places
         | osm | class    | type | addr_place | geometry    |
         | W1  | building | yes  | bar        | (1,2,3,4,1) |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | N9 |

    Scenario: Building in associated street relation
        Given the grid
         | 10 |  |   |   | 11 |
         |    |  | 1 | 2 |    |
         | 12 |  | 4 | 3 |    |
        And the named places
         | osm | class    | type | geometry    |
         | W1  | building | yes  | (1,2,3,4,1) |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | 10,11 |
         | W3  | highway  | residential | foo  | 10,12 |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:house,W3:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W3 |

    Scenario: Building in associated street relation overrides addr:street
        Given the grid
         | 10 |  |   |   | 11 |
         |    |  | 1 | 2 |    |
         | 12 |  | 4 | 3 |    |
        And the named places
         | osm | class    | type | street | geometry    |
         | W1  | building | yes  | foo    | (1,2,3,4,1) |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | 10,11 |
         | W3  | highway  | residential | foo  | 10,12 |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:house,W2:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W2 |

    Scenario: Wrong member in associated street relation is ignored
        Given the grid
         | 10 |   |   |   |   |   |   | 11 |
         |    | 1 |   | 3 | 4 |   |   |    |
         |    |   |   | 6 | 5 |   |   |    |
         And the named places
         | osm | class | type  | geometry |
         | N1  | place | house | 11       |
        And the named places
         | osm | class    | type | street | geometry    |
         | W1  | building | yes  | foo    | (3,4,5,6,3) |
        And the places
         | osm | class    | type        | name | geometry |
         | W3  | highway  | residential | foo  | 10,11    |
        And the relations
         | id | members                      | tags+type |
         | 1  | N1:house,W1:street,W3:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W3 |

    Scenario: street member in associatedStreet relation can be a relation
        Given the grid
          | 1 |   |   | 2 |
          | 3 |   |   | 4 |
          |   |   |   |   |
          |   | 9 |   |   |
          | 5 |   |   | 6 |
        And the places
          | osm | class | type  | housenr | geometry |
          | N9  | place | house | 34      | 9        |
        And the named places
          | osm | class   | type       | name      | geometry    |
          | R14 | highway | pedestrian | Right St  | (1,2,4,3,1) |
          | W14 | highway | pedestrian | Left St   | 5,6         |
        And the relations
          | id | members             | tags+type |
          | 1  | N9:house,R14:street | associatedStreet |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N9     | R14             |


    Scenario: Choose closest street in associatedStreet relation
        Given the grid
         | 1  |   |    |  | 3  |
         | 10 |   | 11 |  | 12 |
        And the places
         | osm | class | type  | housenr | geometry |
         | N1  | place | house | 1       | 1        |
         | N3  | place | house | 3       | 3        |
        And the named places
         | osm  | class    | type        | geometry |
         | W100 | highway  | residential | 10,11    |
         | W101 | highway  | residential | 11,12    |
        And the relations
         | id | members                                            | tags+type |
         | 1  | N1:house,N3:house,W100:street,W101:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W100            |
         | N3     | W101            |


    Scenario: POIs in building inherit address
        Given the grid
         | 10 |  |   |   |   |   | 11 |
         |    |  | 5 | 2 | 6 |   |    |
         |    |  | 3 | 1 |   |   |    |
         | 12 |  | 8 |   | 7 |   |    |
        And the named places
         | osm | class   | type       |
         | N1  | amenity | bank       |
         | N2  | shop    | bakery     |
         | N3  | shop    | supermarket|
        And the places
         | osm | class    | type | street | housenr | geometry    |
         | W1  | building | yes  | foo    | 3       | (5,6,7,8,5) |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | 10,11    |
         | W3  | highway  | residential | foo  | 10,12    |
        When importing
        Then placex contains
         | object | parent_place_id | housenumber |
         | W1     | W3              | 3 |
         | N1     | W3              | 3 |
         | N2     | W3              | 3 |
         | N3     | W3              | 3 |
        When sending geocodejson search query "3, foo" with address
        Then results contain
         | housenumber |
         | 3           |

    Scenario: POIs don't inherit from streets
        Given the grid
         | 10 |   |   |   | 11 |
         |    | 5 | 1 | 6 |    |
         |    | 8 |   | 7 |    |
        And the named places
         | osm | class   | type  |
         | N1  | amenity | bank  |
        And the places
         | osm | class    | type | name | street | housenr | geometry    |
         | W1  | highway  | path | bar  | foo    | 3       | (5,6,7,8,5) |
        And the places
         | osm | class    | type        | name | geometry |
         | W3  | highway  | residential | foo  | 10,11    |
        When importing
        Then placex contains
         | object | parent_place_id | housenumber |
         | N1     | W1              | None |

    Scenario: POIs with own address do not inherit building address
        Given the grid
         | 10 |  |   |   |   |   | 11 |
         |    |  | 6 | 2 | 7 |   |    |
         |    |  | 3 | 1 |   | 5 |  4 |
         | 12 |  | 9 |   | 8 |   |    |
        And the named places
         | osm | class   | type       | street |
         | N1  | amenity | bank       | bar    |
        And the named places
         | osm | class   | type       | housenr |
         | N2  | shop    | bakery     | 4       |
        And the named places
         | osm | class   | type       | addr_place  |
         | N3  | shop    | supermarket| nowhere     |
        And the places
         | osm | class | type              | name     |
         | N4  | place | isolated_dwelling | theplace |
         | N5  | place | isolated_dwelling | nowhere  |
        And the places
         | osm | class    | type | addr_place | housenr | geometry    |
         | W1  | building | yes  | theplace   | 3       | (6,7,8,9,6) |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | 10,11    |
         | W3  | highway  | residential | foo  | 10,12    |
        When importing
        Then placex contains
         | object | parent_place_id | housenumber |
         | W1     | N4              | 3 |
         | N1     | W2              | None |
         | N2     | W2              | 4 |
         | N3     | N5              | None |

    Scenario: POIs parent a road if they are attached to it
        Given the grid
         |    | 10 |    |
         | 20 | 1  | 21 |
         |    | 11 |    |
        And the named places
         | osm | class   | type     |
         | N1  | highway | bus_stop |
        And the places
         | osm | class   | type         | name     | geometry |
         | W1  | highway | secondary    | North St | 10,11 |
         | W2  | highway | unclassified | South St | 20,1,21 |
        And the ways
         | id | nodes |
         | 1  | 10,11 |
         | 2  | 20,1,21 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |

    Scenario: POIs do not parent non-roads they are attached to
        Given the grid
         | 10 |   | 1 |   |  11 |  | 30 |
         | 14 |   |   |   |  15 |  |    |
         | 13 |   | 2 |   |  12 |  | 31 |
        And the named places
         | osm | class   | type     | street   |
         | N1  | highway | bus_stop | North St |
         | N2  | highway | bus_stop | South St |
        And the places
         | osm | class   | type         | name     | geometry |
         | W1  | landuse | residential  | North St | (14,15,12,2,13,14) |
         | W2  | waterway| river        | South St | 10,1,11  |
         | W3  | highway | residential  | foo      | 30,31    |
        And the ways
         | id | nodes |
         | 1  | 10,11,12,2,13,10 |
         | 2  | 10,1,11 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W3 |
         | N2     | W3 |

    Scenario: POIs on building outlines inherit associated street relation
        Given the grid
         | 10 |   |   |   | 11 |
         |    | 5 | 1 | 6 |    |
         | 12 | 8 |   | 7 |    |
        And the named places
         | osm | class    | type  | geometry     |
         | N1  | place    | house | 1            |
         | W1  | building | yes   | (5,1,6,7,8,5)|
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | 10,11    |
         | W3  | highway  | residential | foo  | 10,12    |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:house,W3:street | associatedStreet |
        And the ways
         | id | nodes |
         | 1  | 5,1,6,7,8,5 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W3 |

    # github #1056
    Scenario: Full names should be preferably matched for nearest road
        Given the grid
            | 1 |   | 2 | 5 |
            |   |   |   |   |
            | 3 |   |   | 4 |
            |   | 10|   |   |
        And the places
            | osm | class   | type    | name+name               | geometry |
            | W1  | highway | residential | Via Cavassico superiore | 1, 2 |
            | W3  | highway | residential | Via Cavassico superiore | 2, 5 |
            | W2  | highway | primary | Via Frazione Cavassico  | 3, 4     |
        And the named places
            | osm | class   | type    | addr+street             |
            | N10 | shop    | yes     | Via Cavassico superiore |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N10    | W1 |

     Scenario: place=square may be parented via addr:place
        Given the grid
            |   |   | 9 |   |   |
            |   | 5 |   | 6 |   |
            |   | 8 |   | 7 |   |
        And the places
            | osm | class    | type    | name+name | geometry        |
            | W2  | place    | square  | Foo pl    | (5, 6, 7, 8, 5) |
        And the places
            | osm | class    | type    | name+name | housenr | addr_place | geometry |
            | N10 | shop     | grocery | le shop   | 5       | Foo pl     | 9        |
        When importing
        Then placex contains
            | object | rank_address |
            | W2     | 25           |
        Then placex contains
            | object | parent_place_id |
            | N10    | W2              |


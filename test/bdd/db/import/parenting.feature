@DB
Feature: Parenting of objects
    Tests that the correct parent is chosen

    Scenario: Address inherits postcode from its street unless it has a postcode
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | housenr | geometry |
         | N1  | place | house | 4       | :p-N1 |
        And the places
         | osm | class | type  | housenr | postcode | geometry |
         | N2  | place | house | 5       | 99999    | :p-N1 |
        And the places
         | osm | class   | type        | name  | postcode | geometry |
         | W1  | highway | residential | galoo | 12345    | :w-north |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
        When searching for "4 galoo"
        Then results contain
         | ID | osm_type | osm_id | langaddress
         | 0  | N        | 1      | 4, galoo, 12345
        When searching for "5 galoo"
        Then results contain
         | ID | osm_type | osm_id | langaddress
         | 0  | N        | 2      | 5, galoo, 99999

    Scenario: Address without tags, closest street
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | geometry |
         | N1  | place | house | :p-N1 |
         | N2  | place | house | :p-N2 |
         | N3  | place | house | :p-S1 |
         | N4  | place | house | :p-S2 |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | :w-north |
         | W2  | highway | residential | :w-south |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W2 |

    Scenario: Address without tags avoids unnamed streets
        Given the scene roads-with-pois
        And the places
         | osm | class   | type  | geometry |
         | N1  | place   | house | :p-N1 |
         | N2  | place   | house | :p-N2 |
         | N3  | place   | house | :p-S1 |
         | N4  | place   | house | :p-S2 |
         | W1  | highway | residential | :w-north |
        And the named places
         | osm | class   | type        | geometry |
         | W2  | highway | residential | :w-south |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |
         | N2     | W2 |
         | N3     | W2 |
         | N4     | W2 |

    Scenario: addr:street tag parents to appropriately named street
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | street| geometry |
         | N1  | place | house | south | :p-N1 |
         | N2  | place | house | north | :p-N2 |
         | N3  | place | house | south | :p-S1 |
         | N4  | place | house | north | :p-S2 |
        And the places
         | osm | class   | type        | name  | geometry |
         | W1  | highway | residential | north | :w-north |
         | W2  | highway | residential | south | :w-south |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W1 |

    Scenario: addr:street tag parents to next named street
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | street | geometry |
         | N1  | place | house | abcdef | :p-N1 |
         | N2  | place | house | abcdef | :p-N2 |
         | N3  | place | house | abcdef | :p-S1 |
         | N4  | place | house | abcdef | :p-S2 |
        And the places
         | osm | class   | type        | name   | geometry |
         | W1  | highway | residential | abcdef | :w-north |
         | W2  | highway | residential | abcdef | :w-south |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W2 |

    Scenario: addr:street tag without appropriately named street
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | street | geometry |
         | N1  | place | house | abcdef | :p-N1 |
         | N2  | place | house | abcdef | :p-N2 |
         | N3  | place | house | abcdef | :p-S1 |
         | N4  | place | house | abcdef | :p-S2 |
        And the places
         | osm | class   | type        | name  | geometry |
         | W1  | highway | residential | abcde | :w-north |
         | W2  | highway | residential | abcde | :w-south |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W1 |
         | N3     | W2 |
         | N4     | W2 |

    Scenario: addr:place address
        Given the scene road-with-alley
        And the places
         | osm | class | type   | addr_place | geometry |
         | N1  | place | house  | myhamlet   | :n-alley |
        And the places
         | osm | class   | type        | name     | geometry |
         | N2  | place   | hamlet      | myhamlet | :n-main-west |
         | W1  | highway | residential | myhamlet | :w-main |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | N2 |

    Scenario: addr:street is preferred over addr:place
        Given the scene road-with-alley
        And the places
         | osm | class | type   | addr_place | street  | geometry |
         | N1  | place | house  | myhamlet   | mystreet| :n-alley |
        And the places
         | osm | class   | type        | name     | geometry |
         | N2  | place   | hamlet      | myhamlet | :n-main-west |
         | W1  | highway | residential | mystreet | :w-main |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |

    Scenario: Untagged address in simple associated street relation
        Given the scene road-with-alley
        And the places
         | osm | class | type  | geometry |
         | N1  | place | house | :n-alley |
         | N2  | place | house | :n-corner |
         | N3  | place | house | :n-main-west |
        And the places
         | osm | class   | type        | name | geometry |
         | W1  | highway | residential | foo  | :w-main |
         | W2  | highway | service     | bar  | :w-alley |
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
        Given the scene road-with-alley
        And the places
         | osm | class | type  | geometry |
         | N1  | place | house | :n-alley |
         | N2  | place | house | :n-corner |
         | N3  | place | house | :n-main-west |
         | W2  | highway | residential | :w-alley |
        And the named places
         | osm | class   | type        | geometry |
         | W1  | highway | residential | :w-main |
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
        Given the scene road-with-alley
        And the places
         | osm | class | type  | street | geometry |
         | N1  | place | house | bar    | :n-alley |
        And the places
         | osm | class   | type        | name | geometry |
         | W1  | highway | residential | foo  | :w-main |
         | W2  | highway | residential | bar  | :w-alley |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:street,N1,N2,N3 | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |

    Scenario: Building without tags, closest street from center point
        Given the scene building-on-street-corner
        And the named places
         | osm | class    | type        | geometry |
         | W1  | building | yes         | :w-building |
         | W2  | highway  | primary     | :w-WE |
         | W3  | highway  | residential | :w-NS |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W3 |

    Scenario: Building with addr:street tags
        Given the scene building-on-street-corner
        And the named places
         | osm | class    | type | street | geometry |
         | W1  | building | yes  | bar    | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W2 |

    Scenario: Building with addr:place tags
        Given the scene building-on-street-corner
        And the places
         | osm | class    | type        | name | geometry |
         | N1  | place    | village     | bar  | :n-outer |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        And the named places
         | osm | class    | type | addr_place | geometry |
         | W1  | building | yes  | bar        | :w-building |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | N1 |

    Scenario: Building in associated street relation
        Given the scene building-on-street-corner
        And the named places
         | osm | class    | type | geometry |
         | W1  | building | yes  | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:house,W2:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W2 |

    Scenario: Building in associated street relation overrides addr:street
        Given the scene building-on-street-corner
        And the named places
         | osm | class    | type | street | geometry |
         | W1  | building | yes  | foo    | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:house,W2:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | W1     | W2 |

    Scenario: Wrong member in associated street relation is ignored
        Given the scene building-on-street-corner
        And the named places
         | osm | class | type  | geometry |
         | N1  | place | house | :n-outer |
        And the named places
         | osm | class    | type | street | geometry |
         | W1  | building | yes  | foo    | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        And the relations
         | id | members                      | tags+type |
         | 1  | N1:house,W1:street,W3:street | associatedStreet |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W3 |

    Scenario: POIs in building inherit address
        Given the scene building-on-street-corner
        And the named places
         | osm | class   | type       | geometry |
         | N1  | amenity | bank       | :n-inner |
         | N2  | shop    | bakery     | :n-edge-NS |
         | N3  | shop    | supermarket| :n-edge-WE |
        And the places
         | osm | class    | type | street | addr_place | housenr | geometry |
         | W1  | building | yes  | foo    | nowhere    | 3       | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        When importing
        Then placex contains
         | object | parent_place_id | housenumber |
         | W1     | W3              | 3 |
         | N1     | W3              | 3 |
         | N2     | W3              | 3 |
         | N3     | W3              | 3 |

    Scenario: POIs don't inherit from streets
        Given the scene building-on-street-corner
        And the named places
         | osm | class   | type       | geometry |
         | N1  | amenity | bank       | :n-inner |
        And the places
         | osm | class    | type | street | addr_place | housenr | geometry |
         | W1  | highway  | path | foo    | nowhere    | 3       | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W3  | highway  | residential | foo  | :w-NS |
        When importing
        Then placex contains
         | object | parent_place_id | housenumber |
         | N1     | W3              | None |

    Scenario: POIs with own address do not inherit building address
        Given the scene building-on-street-corner
        And the named places
         | osm | class   | type       | street | geometry |
         | N1  | amenity | bank       | bar    | :n-inner |
        And the named places
         | osm | class   | type       | housenr | geometry |
         | N2  | shop    | bakery     | 4       | :n-edge-NS |
        And the named places
         | osm | class   | type       | addr_place  | geometry |
         | N3  | shop    | supermarket| nowhere     | :n-edge-WE |
        And the places
         | osm | class | type              | name     | geometry |
         | N4  | place | isolated_dwelling | theplace | :n-outer |
        And the places
         | osm | class    | type | addr_place | housenr | geometry |
         | W1  | building | yes  | theplace   | 3       | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        When importing
        Then placex contains
         | object | parent_place_id | housenumber |
         | W1     | N4              | 3 |
         | N1     | W2              | None |
         | N2     | W3              | 4 |
         | N3     | W2              | None |

    Scenario: POIs parent a road if they are attached to it
        Given the scene points-on-roads
        And the named places
         | osm | class   | type     | street   | geometry |
         | N1  | highway | bus_stop | North St | :n-SE |
         | N2  | highway | bus_stop | South St | :n-NW |
         | N3  | highway | bus_stop | North St | :n-S-unglued |
         | N4  | highway | bus_stop | South St | :n-N-unglued |
        And the places
         | osm | class   | type         | name     | geometry |
         | W1  | highway | secondary    | North St | :w-north |
         | W2  | highway | unclassified | South St | :w-south |
        And the ways
         | id | nodes |
         | 1  | 100,101,2,103,104 |
         | 2  | 200,201,1,202,203 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W1 |
         | N2     | W2 |
         | N3     | W1 |
         | N4     | W2 |

    Scenario: POIs do not parent non-roads they are attached to
        Given the scene points-on-roads
        And the named places
         | osm | class   | type     | street   | geometry |
         | N1  | highway | bus_stop | North St | :n-SE |
         | N2  | highway | bus_stop | South St | :n-NW |
        And the places
         | osm | class   | type         | name     | geometry |
         | W1  | landuse | residential  | North St | :w-north |
         | W2  | waterway| river        | South St | :w-south |
        And the ways
         | id | nodes |
         | 1  | 100,101,2,103,104 |
         | 2  | 200,201,1,202,203 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | 0 |
         | N2     | 0 |

    Scenario: POIs on building outlines inherit associated street relation
        Given the scene building-on-street-corner
        And the named places
         | osm | class    | type  | geometry |
         | N1  | place    | house | :n-edge-NS |
         | W1  | building | yes   | :w-building |
        And the places
         | osm | class    | type        | name | geometry |
         | W2  | highway  | primary     | bar  | :w-WE |
         | W3  | highway  | residential | foo  | :w-NS |
        And the relations
         | id | members            | tags+type |
         | 1  | W1:house,W2:street | associatedStreet |
        And the ways
         | id | nodes |
         | 1  | 100,1,101,102,100 |
        When importing
        Then placex contains
         | object | parent_place_id |
         | N1     | W2 |


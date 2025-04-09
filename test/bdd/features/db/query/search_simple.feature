Feature: Searching of simple objects
    Testing simple stuff

    Scenario: Search for place node
        Given the places
          | osm | class | type    | name+name | geometry   |
          | N1  | place | village | Foo       | 10.0 -10.0 |
        When importing
        And geocoding "Foo"
        Then result 0 contains
         | object | category | type    | centroid!wkt |
         | N1     | place    | village | 10 -10   |

    # github #1763
    Scenario: Correct translation of highways under construction
        Given the grid
         | 1 |  |   |  | 2 |
         |   |  | 9 |  |   |
        And the places
         | osm | class   | type         | name      | geometry |
         | W1  | highway | construction | The build | 1,2      |
         | N1  | amenity | cafe         | Bean      | 9        |
        When importing
        And geocoding "Bean"
        Then result 0 contains in field address
         | amenity | road |
         | Bean    | The build |

    Scenario: when missing housenumbers in search don't return a POI
        Given the places
         | osm | class   | type       | name        |
         | N3  | amenity | restaurant | Wood Street |
        And the places
         | osm | class   | type       | name        | housenr |
         | N20 | amenity | restaurant | Red Way     | 34      |
        When importing
        And geocoding "Wood Street 45"
        Then exactly 0 results are returned
        When geocoding "Red Way 34"
        Then all results contain
         | object |
         | N20 |

     Scenario: when the housenumber is missing the street is still returned
        Given the grid
         | 1 |  | 2 |
        Given the places
         | osm | class   | type        | name        | geometry |
         | W1  | highway | residential | Wood Street | 1, 2     |
        When importing
        And geocoding "Wood Street"
        Then all results contain
         | object |
         | W1  |

     Scenario Outline: Special cased american states will be found
        Given the grid
         | 1 |    | 2 |
         |   | 10 |   |
         | 4 |    | 3 |
        Given the places
         | osm  | class    | type           | admin | name    | name+ref | geometry    |
         | R1   | boundary | administrative | 4     | <state> | <ref>    | (1,2,3,4,1) |
        Given the places
         | osm  | class | type  | name   | geometry    |
         | N2   | place | town  | <city> | 10          |
         | N3   | place | city  | <city>  | country:ca  |
        When importing
        And geocoding "<city>, <state>"
        Then all results contain
         | object |
         | N2  |
        When geocoding "<city>, <ref>"
         | accept-language |
         | en |
        Then all results contain
         | object |
         | N2  |

     Examples:
        | city        | state     | ref |
        | Chicago     | Illinois  | IL  |
        | Auburn      | Alabama   | AL  |
        | New Orleans | Louisiana | LA  |

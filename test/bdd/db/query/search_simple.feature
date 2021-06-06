@DB
Feature: Searching of simple objects
    Testing simple stuff

    Scenario: Search for place node
        Given the places
          | osm | class | type    | name+name | geometry   |
          | N1  | place | village | Foo       | 10.0 -10.0 |
        When importing
        And sending search query "Foo"
        Then results contain
         | ID | osm | category | type    | centroid |
         | 0  | N1  | place    | village | 10 -10   |

     Scenario: Updating postcode in postcode boundaries without ref
        Given the places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 12345    | poly-area:1.0 |
        When importing
        And sending search query "12345"
        Then results contain
         | ID | osm |
         | 0  | R1 |
        When updating places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 54321    | poly-area:1.0 |
        And sending search query "12345"
        Then result 0 has not attributes osm_type
        When sending search query "54321"
        Then results contain
         | ID | osm |
         | 0  | R1 |

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
        And sending json search query "Bean" with address
        Then result addresses contain
         | amenity | road |
         | Bean    | The build |

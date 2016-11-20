@DB
Feature: Searching of simple objects
    Testing simple stuff

    Scenario: Search for place node
        Given the places
          | osm | class | type    | name+name | geometry   |
          | N1  | place | village | Foo       | 10.0 -10.0 |
        When importing
        And searching for "Foo"
        Then results contain
         | ID | osm | class | type    | centroid |
         | 0  | N1  | place | village | 10 -10   |

@DB
Feature: Import of simple objects
    Testing simple stuff

    @wip
    Scenario: Import place node
        Given the places
          | osm | class | type    | name | name+ref | geometry   |
          | N1  | place | village | Foo  | 32       | 10.0 -10.0 |
        And the named places
          | osm | class | type    | housenr |
          | N2  | place | village |         |
        When importing
        Then placex contains
          | object | class  | type    | name | name+ref | centroid*10 |
          | N1     | place  | village | Foo  | 32       | 1 -1        |

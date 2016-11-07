@DB
Feature: Import of simple objects
    Testing simple stuff

    @wip
    Scenario: Import place node
        Given the places
          | osm | class | type    | name           | geometry   |
          | N1  | place | village | 'name' : 'Foo' | 10.0 -10.0 |
        And the named places
          | osm | class | type    | housenumber |
          | N2  | place | village |             |
        When importing
        Then table placex contains
          | object | class  | type    | name           | centroid         |
          | N1     | place  | village | 'name' : 'Foo' | 10.0,-10.0 +- 1m |
        When sending query "Foo"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1      |

@DB
Feature: Import of simple objects
    Testing simple stuff

    Scenario: Import place node
        Given the place nodes:
          | osm_id | class | type    | name           | geometry
          | 1      | place | village | 'name' : 'Foo' | 10.0 -10.0
        When importing
        Then table placex contains
          | object | class  | type    | name           | centroid
          | N1     | place  | village | 'name' : 'Foo' | 10.0,-10.0 +- 1m
        When sending query "Foo"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1


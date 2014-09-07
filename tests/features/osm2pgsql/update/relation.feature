@DB
Feature: Update of relations by osm2pgsql
    Testing relation update by osm2pgsql.

Scenario: Remove all members of a relation
        Given the osm nodes:
          | id | tags
          | 1  | 'amenity' : 'prison', 'name' : 'foo'
        Given the osm nodes:
          | id  | geometry
          | 200 | 0 0
          | 201 | 0 0.0001
          | 202 | 0.0001 0.0001
          | 203 | 0.0001 0
        Given the osm ways:
          | id | tags                             | nodes
          | 2  | 'ref' : '45'                     | 200 201 202 203 200
        Given the osm relations:
          | id | tags                                                        | members
          | 1  | 'type' : 'multipolygon', 'tourism' : 'hotel', 'name' : 'XZ' | W2
        When loading osm data
        Then table place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'XZ'
        Given the osm relations:
          | action | id | tags                                                        | members
          | M      | 1  | 'type' : 'multipolygon', 'tourism' : 'hotel', 'name' : 'XZ' | N1
          When updating osm data
        Then table place has no entry for R1


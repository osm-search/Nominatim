@DB
Feature: Update of simple objects by osm2pgsql
    Testing basic update functions of osm2pgsql.

    Scenario: Import object with two main tags
        Given the osm nodes:
          | id | tags
          | 1  | 'tourism' : 'hotel', 'amenity' : 'restaurant', 'name' : 'foo'
        When loading osm data
        Then table place contains
          | object     | class   | type       | name
          | N1:tourism | tourism | hotel      | 'name' : 'foo'
          | N1:amenity | amenity | restaurant | 'name' : 'foo'
        Given the osm nodes:
          | action | id | tags
          | M      | 1  | 'tourism' : 'hotel', 'name' : 'foo'
        When updating osm data
        Then table place has no entry for N1:amenity
        And table place contains
          | object     | class   | type       | name
          | N1:tourism | tourism | hotel      | 'name' : 'foo'


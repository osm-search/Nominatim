@DB
Feature: Import of simple objects by osm2pgsql
    Testing basic tagging in osm2pgsql imports.

    Scenario: Import simple objects
        Given the osm nodes:
          | id | tags
          | 1  | 'amenity' : 'prison', 'name' : 'foo'
        Given the osm nodes:
          | id  | geometry
          | 100 | 0 0
          | 101 | 0 0.1
          | 102 | 0.1 0.2
          | 200 | 0 0
          | 201 | 0 1
          | 202 | 1 1
          | 203 | 1 0
        And the osm ways:
          | id | tags                             | nodes
          | 1  | 'shop' : 'toys', 'name' : 'tata' | 100 101 102
          | 2  | 'ref' : '45'                     | 200 201 202 203 200
        And the osm relations:
          | id | tags                                                        | members
          | 1  | 'type' : 'multipolygon', 'tourism' : 'hotel', 'name' : 'XZ' | N1,W2
        When loading osm data
        Then table place contains
          | object | class   | type   | name
          | N1     | amenity | prison | 'name' : 'foo'
          | W1     | shop    | toys   | 'name' : 'tata'
          | R1     | tourism | hotel  | 'name' : 'XZ'

     Scenario: Import object with two main tags
        Given the osm nodes:
          | id | tags
          | 1  | 'tourism' : 'hotel', 'amenity' : 'restaurant', 'name' : 'foo'
        When loading osm data
        Then table place contains
          | object     | class   | type       | name
          | N1:tourism | tourism | hotel      | 'name' : 'foo'
          | N1:amenity | amenity | restaurant | 'name' : 'foo'

     Scenario: Import stand-alone house number with postcode
        Given the osm nodes:
          | id | tags
          | 1  | 'addr:housenumber' : '4', 'addr:postcode' : '3345'
        When loading osm data
        Then table place contains
          | object | class | type
          | N1     | place | house

     Scenario: Landuses are only imported when named
        Given the osm nodes:
          | id  | geometry
          | 100 | 0 0
          | 101 | 0 0.1
          | 102 | 0.1 0.1
          | 200 | 0 0
          | 202 | 1 1
          | 203 | 1 0
        And the osm ways:
          | id | tags                                          | nodes
          | 1  | 'landuse' : 'residential', 'name' : 'rainbow' | 100 101 102 100
          | 2  | 'landuse' : 'residential'                     | 200 202 203 200
        When loading osm data
        Then table place contains
          | object | class   | type
          | W1     | landuse | residential
        And table place has no entry for W2

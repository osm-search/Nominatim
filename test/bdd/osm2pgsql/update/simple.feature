@DB
Feature: Update of simple objects by osm2pgsql
    Testing basic update functions of osm2pgsql.

    Scenario: Import object with two main tags
        When loading osm data
          """
          n1 Ttourism=hotel,amenity=restaurant,name=foo
          n2 Tplace=locality,name=spotty
          """
        Then place contains
          | object     | type       | name+name |
          | N1:tourism | hotel      | foo |
          | N1:amenity | restaurant | foo |
          | N2:place   | locality   | spotty |
        When updating osm data
          """
          n1 dV Ttourism=hotel,name=foo
          n2 dD
          """
        Then place has no entry for N1:amenity
        And place has no entry for N2
        And place contains
          | object     | class   | type       | name |
          | N1:tourism | tourism | hotel      | 'name' : 'foo' |


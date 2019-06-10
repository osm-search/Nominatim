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

    Scenario: Downgrading a highway to one that is dropped without name
        When loading osm data
          """
          n100 x0 y0
          n101 x0.0001 y0.0001
          w1 Thighway=residential Nn100,n101
          """
        Then place contains
          | object     |
          | W1:highway |
        When updating osm data
          """
          w1 Thighway=service Nn100,n101
          """
        Then place has no entry for W1

    Scenario: Downgrading a highway when a second tag is present
        When loading osm data
          """
          n100 x0 y0
          n101 x0.0001 y0.0001
          w1 Thighway=residential,tourism=hotel Nn100,n101
          """
        Then place contains
          | object     |
          | W1:highway |
          | W1:tourism |
        When updating osm data
          """
          w1 Thighway=service,tourism=hotel Nn100,n101
          """
        Then place has no entry for W1:highway
        And place contains
          | object     |
          | W1:tourism |

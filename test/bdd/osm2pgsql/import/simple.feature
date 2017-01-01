@DB
Feature: Import of simple objects by osm2pgsql
    Testing basic tagging in osm2pgsql imports.

    Scenario: Import simple objects
        When loading osm data
          """
          n1 Tamenity=prison,name=foo x34.3 y-23
          n100 x0 y0
          n101 x0 y0.1
          n102 x0.1 y0.2
          n200 x0 y0
          n201 x0 y1
          n202 x1 y1
          n203 x1 y0
          w1 Tshop=toys,name=tata Nn100,n101,n102
          w2 Tref=45 Nn200,n201,n202,n203,n200
          r1 Ttype=multipolygon,tourism=hotel,name=XZ Mn1@,w2@
          """
        Then place contains exactly
          | object | class   | type   | name            | geometry |
          | N1     | amenity | prison | 'name' : 'foo'  | 34.3 -23 |
          | W1     | shop    | toys   | 'name' : 'tata' | 0 0, 0 0.1, 0.1 0.2 |
          | R1     | tourism | hotel  | 'name' : 'XZ'   | (0 0, 0 1, 1 1, 1 0, 0 0) |

    Scenario: Import object with two main tags
        When loading osm data
          """
          n1 Ttourism=hotel,amenity=restaurant,name=foo
          """
        Then place contains
          | object     | type       | name |
          | N1:tourism | hotel      | 'name' : 'foo' |
          | N1:amenity | restaurant | 'name' : 'foo' |

    Scenario: Import stand-alone house number with postcode
        When loading osm data
          """
          n1 Taddr:housenumber=4,addr:postcode=3345
          """
        Then place contains
          | object | class | type |
          | N1     | place | house |

    Scenario: Landuses are only imported when named
        When loading osm data
          """
          n100 x0 y0
          n101 x0 y0.1
          n102 x0.1 y0.1
          n200 x0 y0
          n202 x1 y1
          n203 x1 y0
          w1 Tlanduse=residential,name=rainbow Nn100,n101,n102,n100
          w2 Tlanduse=residential              Nn200,n202,n203,n200
          """
        Then place contains exactly
          | object | class   | type |
          | W1     | landuse | residential |

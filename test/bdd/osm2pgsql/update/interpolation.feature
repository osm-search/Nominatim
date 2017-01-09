@DB
Feature: Update of interpolations

    @wip
    # Test case for #598
    Scenario: add an interpolation way
        Given the grid
          | 4 | 7 | 5 |
          | 10|   | 12|
        When loading osm data
          """
          n3
          n4 Taddr:housenumber=1
          n5 Taddr:housenumber=5
          n10
          n12
          w11 Thighway=residential,name=X Nn4,n5
          w12 Thighway=residential,name=Highway Nn10,n12
          """
        And updating osm data
          """
          n4 Taddr:housenumber=1
          n5 Taddr:housenumber=5
          w1 Taddr:interpolation=odd Nn4,n5
          w2 Tbuilding=yes,name=ggg Nn4,n10,n7,n4
          w3 Tbuilding=yes,name=ggg Nn4,n10,n7,n4
          w4 Tbuilding=yes,name=ggg Nn4,n10,n7,n4
          w5 Tbuilding=yes,name=ggg Nn4,n10,n7,n4
          w6 Tbuilding=yes,name=ggg Nn4,n10,n7,n4
          w7 Tbuilding=yes,name=ggg Nn4,n10,n7,n4
          w11 dD
          """
        Then place contains
          | object   | housenumber |
          | N4:place | 1           |
          | N5:place | 5           |
          | W1:place | odd         |
        And W1 expands to interpolation
          | start | end |
          | 1     | 5   |

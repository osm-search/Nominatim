Feature: Import of objects with broken geometries by osm2pgsql

    Scenario: Import way with double nodes
        When loading osm data
          """
          n100 x0 y0
          n101 x0 y0.1
          n102 x0.1 y0.2
          w1 Thighway=primary Nn100,n101,n101,n102
          """
        Then place contains
          | object | class   | type    | geometry!wkt |
          | W1     | highway | primary | 0 0, 0 0.1, 0.1 0.2 |

    Scenario: Import of ballon areas
        Given the grid
         | 2 |  | 3 |
         | 1 |  | 4 |
         | 5 |  |   |
        When loading osm data
          """
          n1
          n2
          n3
          n4
          n5
          w1 Thighway=unclassified Nn1,n2,n3,n4,n1,n5
          w2 Thighway=unclassified Nn1,n2,n3,n4,n1
          w3 Thighway=unclassified Nn1,n2,n3,n4,n3
          """
        Then place contains
          | object | geometry!wkt |
          | W1     | 1,2,3,4,1,5  |
          | W2     | (1,2,3,4,1)  |
          | W3     | 1,2,3,4      |

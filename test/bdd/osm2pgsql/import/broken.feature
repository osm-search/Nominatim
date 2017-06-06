@DB
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
          | object | class   | type    | geometry |
          | W1     | highway | primary | 0 0, 0 0.1, 0.1 0.2 |

    Scenario: Import of ballon areas
        When loading osm data
          """
          n1   x0 y0
          n2   x0 y0.0001
          n3   x0.00001 y0.0001
          n4   x0.00001 y0
          n5   x-0.00001 y0
          w1 Thighway=unclassified Nn1,n2,n3,n4,n1,n5
          w2 Thighway=unclassified Nn1,n2,n3,n4,n1
          w3 Thighway=unclassified Nn1,n2,n3,n4,n3
          """
        Then place contains
          | object | geometrytype |
          | W1     | ST_LineString |
          | W2     | ST_Polygon |
          | W3     | ST_LineString |

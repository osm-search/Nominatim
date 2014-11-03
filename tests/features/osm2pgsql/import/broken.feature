@DB
Feature: Import of objects with broken geometries by osm2pgsql

    @Fail
    Scenario: Import way with double nodes
        Given the osm nodes:
          | id  | geometry
          | 100 | 0 0
          | 101 | 0 0.1
          | 102 | 0.1 0.2
        And the osm ways:
          | id | tags                  | nodes
          | 1  | 'highway' : 'primary' | 100 101 101 102
        When loading osm data
        Then table place contains
          | object | class   | type    | geometry
          | W1     | highway | primary | (0 0, 0 0.1, 0.1 0.2)

    Scenario: Import of ballon areas
        Given the osm nodes:
          | id  | geometry
          | 1   | 0 0
          | 2   | 0 0.0001
          | 3   | 0.00001 0.0001
          | 4   | 0.00001 0
          | 5   | -0.00001 0
        And the osm ways:
          | id | tags                       | nodes
          | 1  | 'highway' : 'unclassified' | 1 2 3 4 1 5
          | 2  | 'highway' : 'unclassified' | 1 2 3 4 1
          | 3  | 'highway' : 'unclassified' | 1 2 3 4 3
        When loading osm data
        Then table place contains
          | object | geometrytype
          | W1     | ST_LineString
          | W2     | ST_Polygon
          | W3     | ST_LineString

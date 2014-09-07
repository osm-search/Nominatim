@DB
Feature: Import of relations by osm2pgsql
    Testing specific relation problems related to members.

    Scenario: Don't import empty waterways
        Given the osm nodes:
          | id | tags
          | 1  | 'amenity' : 'prison', 'name' : 'foo'
        And the osm relations:
          | id | tags                                                     | members
          | 1  | 'type' : 'waterway', 'waterway' : 'river', 'name' : 'XZ' | N1
        When loading osm data
        Then table place has no entry for R1

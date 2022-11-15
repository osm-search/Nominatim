@DB
Feature: Update of simple objects by osm2pgsql
    Testing basic update functions of osm2pgsql.

    Scenario: Adding a new object
        When loading osm data
          """
          n1 Tplace=town,name=Middletown
          """
        Then place contains exactly
          | object   | type | name+name  |
          | N1:place | town | Middletown |

       When updating osm data
         """
         n2 Tamenity=hotel,name=Posthotel
         """
        Then place contains exactly
          | object     | type  | name+name  |
          | N1:place   | town  | Middletown |
          | N2:amenity | hotel | Posthotel  |
        And placex contains exactly
          | object     | type  | name+name  | indexed_status |
          | N1:place   | town  | Middletown | 0              |
          | N2:amenity | hotel | Posthotel  | 1              |


    Scenario: Deleting an existing object
        When loading osm data
          """
          n1 Tplace=town,name=Middletown
          n2 Tamenity=hotel,name=Posthotel
          """
        Then place contains exactly
          | object     | type  | name+name  |
          | N1:place   | town  | Middletown |
          | N2:amenity | hotel | Posthotel  |

       When updating osm data
         """
         n2 dD
         """
        Then place contains exactly
          | object     | type  | name+name  |
          | N1:place   | town  | Middletown |
        And placex contains exactly
          | object     | type  | name+name  | indexed_status |
          | N1:place   | town  | Middletown | 0              |
          | N2:amenity | hotel | Posthotel  | 100            |

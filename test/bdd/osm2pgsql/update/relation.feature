@DB
Feature: Update of relations by osm2pgsql
    Testing relation update by osm2pgsql.

    Scenario: Remove all members of a relation
        When loading osm data
          """
          n1 Tamenity=prison,name=foo
          n200 x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          w2 Tref=45' Nn200,n201,n202,n203,n200
          r1 Ttype=multipolygon,tourism=hotel,name=XZ' Mw2@
          """
        Then place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'XZ'
          When updating osm data
            """
            r1 Ttype=multipolygon,tourism=hotel,name=XZ Mn1@
            """
        Then place has no entry for R1


    Scenario: Change type of a relation
        When loading osm data
          """
          n200 x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          w2 Tref=45 Nn200,n201,n202,n203,n200
          r1 Ttype=multipolygon,tourism=hotel,name=XZ Mw2@
          """
        Then place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'XZ'
        When updating osm data
          """
          r1 Ttype=multipolygon,amenity=prison,name=XZ Mw2@
          """
        Then place has no entry for R1:tourism
        And place contains
          | object | class   | type   | name
          | R1     | amenity | prison | 'name' : 'XZ'

    Scenario: Change name of a relation
        When loading osm data
          """
          n200 x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          w2 Tref=45 Nn200,n201,n202,n203,n200
          r1 Ttype=multipolygon,tourism=hotel,name=AB Mw2@
          """
        Then place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'AB'
        When updating osm data
          """
          r1 Ttype=multipolygon,tourism=hotel,name=XY Mw2@
          """
        Then place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'XZ'

    Scenario: Change type of a relation into something unknown
        When loading osm data
          """
          n200 x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          w2 Tref=45 Nn200,n201,n202,n203,n200
          r1 Ttype=multipolygon,tourism=hotel,name=XY Mw2@
          """
        Then place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'XZ'
        When updating osm data
          """
          r1 Ttype=multipolygon,amenities=prison,name=XY Mw2@
          """
        Then place has no entry for R1

    Scenario: Type tag is removed
        When loading osm data
          """
          n200 x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          w2 Tref=45 Nn200,n201,n202,n203,n200
          r1 Ttype=multipolygon,tourism=hotel,name=XY Mw2@
          """
        Then place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'XZ'
        When updating osm data
          """
          r1 Ttourism=hotel,name=XY Mw2@
          """
        Then place has no entry for R1

    Scenario: Type tag is renamed to something unknown
        When loading osm data
          """
          n200 x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          w2 Tref=45 Nn200,n201,n202,n203,n200
          r1 Ttype=multipolygon,tourism=hotel,name=XY Mw2@
          """
        Then place contains
          | object | class   | type   | name
          | R1     | tourism | hotel  | 'name' : 'XZ'
        When updating osm data
          """
          r1 Ttype=multipolygonn,tourism=hotel,name=XY Mw2@
          """
        Then place has no entry for R1

    Scenario: Country boundary names are left untouched when country_code unknown
        When loading osm data
          """
          n200 Tamenity=prison x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          """
        And updating osm data
          """
          w1 Nn200,n201,n202,n203,n200
          r1 Ttype=boundary,boundary=administrative,name=Foo,country_code=XX,admin_level=2 Mw1@
          """
        Then place contains
          | object | country_code | name           |
          | R1     | XX           | 'name' : 'Foo' |

    Scenario: Country boundary names are extended when country_code known
        When loading osm data
          """
          n200 Tamenity=prison x0 y0
          n201 x0 y0.0001
          n202 x0.0001 y0.0001
          n203 x0.0001 y0
          """
        And updating osm data
          """
          w1 Nn200,n201,n202,n203,n200
          r1 Ttype=boundary,boundary=administrative,name=Foo,country_code=ch,admin_level=2 Mw1@
          """
        Then place contains
            | object | country_code | name+name:de | name+name |
            | R1     | ch           | Schweiz      | Foo       |


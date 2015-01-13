@DB
Feature: Tag evaluation
    Tests if tags are correctly imported into the place table

    Scenario Outline: Name tags
        Given the osm nodes:
         | id | tags
         | 1  | 'highway' : 'yes', '<nametag>' : 'Foo'
        When loading osm data
        Then table place contains
         | object | name
         | N1     | '<nametag>' : 'Foo'

    Examples:
     | nametag
     | ref
     | int_ref
     | nat_ref
     | reg_ref
     | loc_ref
     | old_ref
     | iata
     | icao
     | pcode:1
     | pcode:2
     | pcode:3
     | name
     | name:de
     | name:bt-BR
     | int_name
     | int_name:xxx
     | nat_name
     | nat_name:fr
     | reg_name
     | reg_name:1
     | loc_name
     | loc_name:DE
     | old_name
     | old_name:v1
     | alt_name
     | alt_name:dfe
     | alt_name_1
     | official_name
     | common_name
     | common_name:pot
     | short_name
     | short_name:CH
     | operator
     | addr:housename

    Scenario Outline: Ignored name tags
        Given the osm nodes:
         | id | tags
         | 1  | 'highway' : 'yes', '<nametag>' : 'Foo', 'name' : 'real'
        When loading osm data
        Then table place contains
         | object | name
         | N1     | 'name' : 'real'

    Examples:
     | nametag
     | name_de
     | Name
     | ref:de
     | ref_de
     | my:ref
     | br:name
     | name:prefix

    Scenario: Special character in name tag
        Given the osm nodes:
         | id | tags
         | 1  | 'highway' : 'yes', 'name: de' : 'Foo', 'name' : 'real'
         | 2  | 'highway' : 'yes', 'name:\nde' : 'Foo', 'name' : 'real'
         | 3  | 'highway' : 'yes', 'name:\tde' : 'Foo', 'name:\\' : 'real'
        When loading osm data
        Then table place contains
         | object | name
         | N1     | 'name:_de' : 'Foo', 'name' : 'real'
         | N2     | 'name:_de' : 'Foo', 'name' : 'real'
         | N3     | 'name:_de' : 'Foo', 'name:\\\\' : 'real'

    Scenario Outline: Included places
        Given the osm nodes:
         | id | tags
         | 1  | '<key>' : '<value>', 'name' : 'real'
        When loading osm data
        Then table place contains
         | object | name
         | N1     | 'name' : 'real'

    Examples:
     | key       | value
     | emergency | phone
     | tourism   | information
     | historic  | castle
     | military  | barracks
     | natural   | water
     | highway   | residential
     | aerialway | station
     | aeroway   | way
     | boundary  | administrative
     | bridge    | yes
     | craft     | butcher
     | leisure   | playground
     | office    | bookmaker
     | railway   | rail
     | shop      | bookshop
     | tunnel    | yes
     | waterway  | stream
     | landuse   | cemetry



    Scenario Outline: Excluded places
        Given the osm nodes:
         | id | tags
         | 1  | '<key>' : '<value>', 'name' : 'real'
         | 2  | 'highway' : 'motorway', 'name' : 'To Hell'
        When loading osm data
        Then table place has no entry for N1

    Examples:
     | key       | value
     | emergency | yes
     | emergency | no
     | tourism   | yes
     | tourism   | no
     | historic  | yes
     | historic  | no
     | military  | yes
     | military  | no
     | natural   | yes
     | natural   | no
     | highway   | no
     | highway   | turning_circle
     | highway   | traffic_signals
     | highway   | mini_roundabout
     | highway   | noexit
     | highway   | crossing
     | aerialway | no
     | aeroway   | no
     | amenity   | no
     | boundary  | no
     | bridge    | no
     | craft     | no
     | leisure   | no
     | office    | no
     | railway   | no
     | shop      | no
     | tunnel    | no
     | waterway  | riverbank


    Scenario: Boundary with place tag
        Given the osm nodes:
          | id  | geometry
          | 200 | 0 0
          | 201 | 0 1
          | 202 | 1 1
          | 203 | 1 0
        And the osm ways:
          | id | tags                                           | nodes
          | 2  | 'boundary' : 'administrative', 'place' : 'city' | 200 201 202 203 200
          | 20 | 'place' : 'city'                                | 200 201 202 203 200
          | 40 | 'place' : 'city', 'boundary' : 'statistical'    | 200 201 202 203 200
        When loading osm data
        Then table place contains
          | object       | class    | type           | extratags
          | W2           | boundary | administrative | 'place' : 'city'
          | W20          | place    | city           |
          | W40:boundary | boundary | statistical    |
          | W40:place    | place    | city           |
        And table place has no entry for W2:place

    Scenario Outline: Tags that describe a house
        Given the osm nodes:
          | id  | tags
          | 100 | '<key>' : '<value>'
          | 999 | 'amenity' : 'prison', '<key>' : '<value>'
        When loading osm data
        Then table place contains
          | object | class   | type
          | N100   | place   | house
          | N999   | amenity | prison
        And table place has no entry for N100:<key>
        And table place has no entry for N999:<key>
        And table place has no entry for N999:place

    Examples:
      | key                     | value
      | addr:housename          | My Mansion
      | addr:housenumber        | 456
      | addr:conscriptionnumber | 4
      | addr:streetnumber       | 4568765

    Scenario: Only named with no other interesting tag
        Given the osm nodes:
          | id  | tags
          | 1   | 'landuse' : 'meadow'
          | 2   | 'landuse' : 'residential', 'name' : 'important'
          | 3   | 'landuse' : 'residential', 'name' : 'important', 'place' : 'hamlet'
        When loading osm data
        Then table place contains
          | object | class   | type
          | N2     | landuse | residential
          | N3     | place   | hamlet
        And table place has no entry for N1
        And table place has no entry for N3:landuse

    Scenario Outline: Import of postal codes
        Given the osm nodes:
          | id  | tags
          | 10  | 'place' : 'village', '<key>' : '<value>'
        When loading osm data
        Then table place contains
          | object | class   | type    | postcode
          | N10    | place   | village | <value>

    Examples:
      | key              | value
      | postal_code      | 45736
      | post_code        | gf4 65g
      | postcode         | xxx
      | addr:postcode    | 564
      | tiger:zip_left   | 00011
      | tiger:zip_right  | 09123

    Scenario: Import of street and place
        Given the osm nodes:
          | id  | tags
          | 10  | 'amenity' : 'hospital', 'addr:street' : 'Foo St'
          | 20  | 'amenity' : 'hospital', 'addr:place' : 'Foo Town'
        When loading osm data
        Then table place contains
          | object | class   | type     | street  | addr_place
          | N10    | amenity | hospital | Foo St  | None
          | N20    | amenity | hospital | None    | Foo Town


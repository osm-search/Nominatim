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
     | mountain_pass | yes


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
          | 10  | 'highway' : 'secondary', '<key>' : '<value>'
          | 11  | '<key>' : '<value>'
        When loading osm data
        Then table place contains
          | object | class   | type      | postcode
          | N10    | highway | secondary | <value>
          | N11    | place   | postcode  | <value>
        And table place has no entry for N10:place

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


    Scenario Outline: Import of country
        Given the osm nodes:
          | id  | tags
          | 10  | 'place' : 'village', '<key>' : '<value>'
        When loading osm data
        Then table place contains
          | object | class   | type    | country_code
          | N10    | place   | village | <value>

    Examples:
        | key                            | value
        | country_code_iso3166_1_alpha_2 | gb
        | country_code_iso3166_1         | UK
        | country_code_iso3166           | de
        | country_code                   | us
        | iso3166-1:alpha2               | aU
        | iso3166-1                      | 12
        | ISO3166-1                      | XX
        | iso3166                        | Nl
        | is_in:country_code             | __
        | addr:country                   | ..
        | addr:country_code              | cv

    Scenario Outline: Ignore country codes with wrong length
        Given the osm nodes:
          | id  | tags
          | 10  | 'place' : 'village', 'country_code' : '<value>'
        When loading osm data
        Then table place contains
          | object | class   | type    | country_code
          | N10    | place   | village | None

    Examples:
        | value
        | X
        | x
        | ger
        | dkeufr
        | d e

    Scenario: Import of house numbers
        Given the osm nodes:
          | id  | tags
          | 10  | 'building' : 'yes', 'addr:housenumber' : '4b'
          | 11  | 'building' : 'yes', 'addr:conscriptionnumber' : '003'
          | 12  | 'building' : 'yes', 'addr:streetnumber' : '2345'
          | 13  | 'building' : 'yes', 'addr:conscriptionnumber' : '3', 'addr:streetnumber' : '111'
        When loading osm data
        Then table place contains
          | object | class | type   | housenumber
          | N10    | place | house  | 4b
          | N11    | place | house  | 003
          | N12    | place | house  | 2345
          | N13    | place | house  | 3/111

    Scenario: Import of address interpolations
        Given the osm nodes:
          | id  | tags
          | 10  | 'addr:interpolation' : 'odd'
          | 11  | 'addr:housenumber' : '10', 'addr:interpolation' : 'odd'
          | 12  | 'addr:interpolation' : 'odd', 'addr:housenumber' : '23'
        When loading osm data
        Then table place contains
          | object | class   | type    | housenumber
          | N10    | place   | houses  | odd
          | N11    | place   | houses  | odd
          | N12    | place   | houses  | odd

    Scenario: Shorten tiger:county tags
        Given the osm nodes:
          | id  | tags
          | 10  | 'place' : 'village', 'tiger:county' : 'Feebourgh, AL'
          | 11  | 'place' : 'village', 'addr:state' : 'Alabama', 'tiger:county' : 'Feebourgh, AL'
        When loading osm data
        Then table place contains
          | object | class   | type    | isin
          | N10    | place   | village | Feebourgh county
          | N11    | place   | village | Alabama,Feebourgh county

    Scenario Outline: Import of address tags
        Given the osm nodes:
          | id  | tags
          | 10  | 'place' : 'village', '<key>' : '<value>'
        When loading osm data
        Then table place contains
          | object | class   | type    | isin
          | N10    | place   | village | <value>

    Examples:
      | key             | value
      | is_in           | Stockholm, Sweden
      | is_in:country   | Xanadu
      | addr:suburb     | hinein
      | addr:county     | le havre
      | addr:city       | Sydney
      | addr:state      | Jura

    Scenario: Import of admin level
        Given the osm nodes:
          | id  | tags
          | 10  | 'amenity' : 'hospital', 'admin_level' : '3'
          | 11  | 'amenity' : 'hospital', 'admin_level' : 'b'
        When loading osm data
        Then table place contains
          | object | class   | type     | admin_level
          | N10    | amenity | hospital | 3
          | N11    | amenity | hospital | 0

    Scenario: Import of extra tags
        Given the osm nodes:
          | id  | tags
          | 10  | 'tourism' : 'hotel', '<key>' : 'foo'
        When loading osm data
        Then table place contains
          | object | class   | type  | extratags
          | N10    | tourism | hotel | '<key>' : 'foo'

     Examples:
       | key
       | tracktype
       | traffic_calming
       | service
       | cuisine
       | capital
       | dispensing
       | religion
       | denomination
       | sport
       | internet_access
       | lanes
       | surface
       | smoothness
       | width
       | est_width
       | incline
       | opening_hours
       | food_hours
       | collection_times
       | service_times
       | smoking_hours
       | disused
       | wheelchair
       | sac_scale
       | trail_visibility
       | mtb:scale
       | mtb:description
       | wood
       | drive_thru
       | drive_in
       | access
       | vehicle
       | bicyle
       | foot
       | goods
       | hgv
       | motor_vehicle
       | motor_car
       | access:foot
       | contact:phone
       | drink:mate
       | oneway
       | date_on
       | date_off
       | day_on
       | day_off
       | hour_on
       | hour_off
       | maxweight
       | maxheight
       | maxspeed
       | disused
       | toll
       | charge
       | population
       | description
       | image
       | attribution
       | fax
       | email
       | url
       | website
       | phone
       | tel
       | real_ale
       | smoking
       | food
       | camera
       | brewery
       | locality
       | wikipedia
       | wikipedia:de

    Scenario: buildings
        Given the osm nodes:
          | id  | tags
          | 10  | 'tourism' : 'hotel', 'building' : 'yes'
          | 11  | 'building' : 'house'
          | 12  | 'building' : 'shed', 'addr:housenumber' : '1'
          | 13  | 'building' : 'yes', 'name' : 'Das Haus'
          | 14  | 'building' : 'yes', 'addr:postcode' : '12345'
        When loading osm data
        Then table place contains
          | object | class   | type
          | N10    | tourism | hotel
          | N12    | place   | house
          | N13    | building| yes
          | N14    | building| yes
        And table place has no entry for N10:building
        And table place has no entry for N11

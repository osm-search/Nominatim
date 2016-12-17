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
     | short_name
     | short_name:CH
     | addr:housename
     | brand

    Scenario Outline: operator only for shops and amenities
        Given the osm nodes:
         | id | tags
         | 1  | 'highway' : 'yes', 'operator' : 'Foo', 'name' : 'null'
         | 2  | 'shop' : 'grocery', 'operator' : 'Foo'
         | 3  | 'amenity' : 'hospital', 'operator' : 'Foo'
         | 4  | 'tourism' : 'hotel', 'operator' : 'Foo'
        When loading osm data
        Then table place contains
         | object | name
         | N1     | 'name' : 'null'
         | N2     | 'operator' : 'Foo'
         | N3     | 'operator' : 'Foo'
         | N4     | 'operator' : 'Foo'

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
     | name:source

    Scenario: Special character in name tag
        Given the osm nodes:
         | id | tags
         | 1  | 'highway' : 'yes', 'name: de' : 'Foo', 'name' : 'real1'
         | 2  | 'highway' : 'yes', 'name:&#xa;de' : 'Foo', 'name' : 'real2'
         | 3  | 'highway' : 'yes', 'name:&#x9;de' : 'Foo', 'name:\\' : 'real3'
        When loading osm data
        Then table place contains
         | object | name
         | N1     | 'name: de' : 'Foo', 'name' : 'real1'
         | N2     | 'name: de' : 'Foo', 'name' : 'real2'
         | N3     | 'name: de' : 'Foo', 'name:\\' : 'real3'

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
     | craft     | butcher
     | leisure   | playground
     | office    | bookmaker
     | railway   | rail
     | shop      | bookshop
     | waterway  | stream
     | landuse   | cemetry
     | man_made  | tower
     | mountain_pass | yes

    Scenario Outline: Bridges and Tunnels take special name tags
        Given the osm nodes:
          | id | tags
          | 1  | 'highway' : 'road', '<key>' : 'yes', 'name' : 'Rd', '<key>:name' : 'My'
          | 2  | 'highway' : 'road', '<key>' : 'yes', 'name' : 'Rd'
        When loading osm data
        Then table place contains
          | object     | class   | type | name
          | N1:highway | highway | road | 'name' : 'Rd'
          | N1:<key>   | <key>   | yes  | 'name' : 'My'
          | N2:highway | highway | road | 'name' : 'Rd'
        And table place has no entry for N2:<key>

    Examples:
      | key
      | bridge
      | tunnel

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
     | highway   | mini_roundabout
     | highway   | noexit
     | highway   | crossing
     | aerialway | no
     | aerialway | pylon
     | man_made  | survey_point
     | man_made  | cutline
     | aeroway   | no
     | amenity   | no
     | bridge    | no
     | craft     | no
     | leisure   | no
     | office    | no
     | railway   | no
     | railway   | level_crossing
     | shop      | no
     | tunnel    | no
     | waterway  | riverbank

    Scenario: Some tags only are included when named
        Given the osm nodes:
         | id | tags
         | 1  | '<key>' : '<value>'
         | 2  | '<key>' : '<value>', 'name' : 'To Hell'
         | 3  | '<key>' : '<value>', 'ref' : '123'
        When loading osm data
        Then table place has no entry for N1
        And table place has no entry for N3
        And table place contains
         | object | class | type
         | N2     | <key> | <value>

    Examples:
      | key      | value
      | landuse  | residential
      | natural  | meadow
      | highway  | traffic_signals
      | highway  | service
      | highway  | cycleway
      | highway  | path
      | highway  | footway
      | highway  | steps
      | highway  | bridleway
      | highway  | track
      | highway  | byway
      | highway  | motorway_link
      | highway  | primary_link
      | highway  | trunk_link
      | highway  | secondary_link
      | highway  | tertiary_link
      | railway  | rail
      | boundary | administrative
      | waterway | stream

    Scenario: Footways are not included if they are sidewalks
        Given the osm nodes:
         | id | tags
         | 2  | 'highway' : 'footway', 'name' : 'To Hell', 'footway' : 'sidewalk'
         | 23 | 'highway' : 'footway', 'name' : 'x'
        When loading osm data
        Then table place has no entry for N2

    Scenario: named junctions are included if there is no other tag
        Given the osm nodes:
         | id | tags
         | 1  | 'junction' : 'yes'
         | 2  | 'highway' : 'secondary', 'junction' : 'roundabout', 'name' : 'To Hell'
         | 3  | 'junction' : 'yes', 'name' : 'Le Croix'
        When loading osm data
        Then table place has no entry for N1
        And table place has no entry for N2:junction
        And table place contains
         | object | class    | type
         | N3     | junction | yes

    Scenario: Boundary with place tag
        Given the osm nodes:
          | id  | geometry
          | 200 | 0 0
          | 201 | 0 1
          | 202 | 1 1
          | 203 | 1 0
        And the osm ways:
          | id | tags                                                              | nodes
          | 2  | 'boundary' : 'administrative', 'place' : 'city', 'name' : 'Foo'   | 200 201 202 203 200
          | 4  | 'boundary' : 'administrative', 'place' : 'island','name' : 'Foo'  | 200 201 202 203 200
          | 20 | 'place' : 'city', 'name' : 'ngng'                                 | 200 201 202 203 200
          | 40 | 'place' : 'city', 'boundary' : 'statistical', 'name' : 'BB'       | 200 201 202 203 200
        When loading osm data
        Then table place contains
          | object       | class    | extratags        | type
          | W2           | boundary | 'place' : 'city' | administrative
          | W4:boundary  | boundary | None             | administrative
          | W4:place     | place    | None             | island
          | W20          | place    | None             | city
          | W40:boundary | boundary | None             | statistical
          | W40:place    | place    | None             | city
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
        | country_code                   | us
        | ISO3166-1                      | XX
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
          | N10    | building | yes  | 4b
          | N11    | building | yes  | 003
          | N12    | building | yes  | 2345
          | N13    | building | yes  | 3/111

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
          | 12  | 'place' : 'village', 'tiger:county' : 'Feebourgh'
        When loading osm data
        Then table place contains
          | object | class   | type    | isin
          | N10    | place   | village | Feebourgh county
          | N11    | place   | village | Feebourgh county,Alabama
          | N12    | place   | village | Feebourgh county

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
          | 12  | 'amenity' : 'hospital'
          | 13  | 'amenity' : 'hospital', 'admin_level' : '3.0'
        When loading osm data
        Then table place contains
          | object | class   | type     | admin_level
          | N10    | amenity | hospital | 3
          | N11    | amenity | hospital | 100
          | N12    | amenity | hospital | 100
          | N13    | amenity | hospital | 3

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
       | collection_times
       | service_times
       | disused
       | wheelchair
       | sac_scale
       | trail_visibility
       | mtb:scale
       | mtb:description
       | wood
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
       | real_ale
       | smoking
       | food
       | camera
       | brewery
       | locality
       | wikipedia
       | wikipedia:de
       | wikidata
       | name:prefix
       | name:botanical
       | name:etymology:wikidata

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
          | N12    | building| yes
          | N13    | building| yes
          | N14    | building| yes
        And table place has no entry for N10:building
        And table place has no entry for N11

   Scenario: complete node entry
       Given the osm nodes:
         | id        | tags
         | 290393920 | 'addr:city':'Perpignan','addr:country':'FR','addr:housenumber':'43\\','addr:postcode':'66000','addr:street':'Rue Pierre Constant d`Ivry','source':'cadastre-dgi-fr source : Direction Générale des Impôts - Cadastre ; mise à jour :2008'
        When loading osm data
        Then table place contains
         | object     | class   | type | housenumber
         | N290393920 | place   | house| 43\

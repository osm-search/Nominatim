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
     : br:name

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

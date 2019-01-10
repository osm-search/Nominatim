@DB
Feature: Tag evaluation
    Tests if tags are correctly imported into the place table

    Scenario Outline: Name tags
       When loading osm data
         """
         n1 Thighway=yes,<nametag>=Foo
         """
       Then place contains
         | object | name |
         | N1     | '<nametag>' : 'Foo' |

    Examples:
     | nametag |
     | ref |
     | int_ref |
     | nat_ref |
     | reg_ref |
     | loc_ref |
     | old_ref |
     | iata |
     | icao |
     | pcode:1 |
     | pcode:2 |
     | pcode:3 |
     | name |
     | name:de |
     | name:bt-BR |
     | int_name |
     | int_name:xxx |
     | nat_name |
     | nat_name:fr |
     | reg_name |
     | reg_name:1 |
     | loc_name |
     | loc_name:DE |
     | old_name |
     | old_name:v1 |
     | alt_name |
     | alt_name:dfe |
     | alt_name_1 |
     | official_name |
     | short_name |
     | short_name:CH |
     | addr:housename |
     | brand |

    Scenario: operator only for shops and amenities
        When loading osm data
         """
         n1 Thighway=yes,operator=Foo,name=null
         n2 Tshop=grocery,operator=Foo
         n3 Tamenity=restaurant,operator=Foo
         n4 Ttourism=hotel,operator=Foo
         n5 Tamenity=hospital,operator=Foo,name=Meme
         n6 Tamenity=fuel,operator=Foo
         """
        Then place contains
         | object | name |
         | N1     | 'name' : 'null' |
         | N2     | 'operator' : 'Foo' |
         | N3     | 'operator' : 'Foo' |
         | N4     | 'operator' : 'Foo' |
         | N5     | 'name' : 'Meme' |
         | N6     | 'operator' : 'Foo' |

    Scenario Outline: Ignored name tags
        When loading osm data
         """
         n1 Thighway=yes,<nametag>=Foo,name=real
         """
        Then place contains
         | object | name |
         | N1     | 'name' : 'real' |

    Examples:
     | nametag |
     | name_de |
     | Name |
     | ref:de |
     | ref_de |
     | my:ref |
     | br:name |
     | name:prefix |
     | name:source |

    Scenario: Special character in name tag
        When loading osm data
         """
         n1 Thighway=yes,name:%20%de=Foo,name=real1
         n2 Thighway=yes,name:%a%de=Foo,name=real2
         n3 Thighway=yes,name:%9%de=Foo,name:\\=real3
         n4 Thighway=yes,name:%9%de=Foo,name=rea\l3
         """
        Then place contains
         | object | name |
         | N1     | 'name: de' : 'Foo', 'name' : 'real1' |
         | N2     | 'name: de' : 'Foo', 'name' : 'real2' |
         | N3     | 'name: de' : 'Foo', 'name:\\\\' : 'real3' |
         | N4     | 'name: de' : 'Foo', 'name' : 'rea\\l3' |

    Scenario: Unprintable character in address tag are maintained
        When loading osm data
         """
         n23 Tamenity=yes,name=foo,addr:postcode=1234%200e%
         """
        Then place contains
         | object | address |
         | N23    | 'postcode' : u'1234\u200e' |

    Scenario Outline: Included places
        When loading osm data
         """
         n1 T<key>=<value>,name=real
         """
        Then place contains
         | object | class | type    | name |
         | N1     | <key> | <value> | 'name' : 'real' |

    Examples:
     | key       | value |
     | emergency | phone |
     | tourism   | information |
     | historic  | castle |
     | military  | barracks |
     | natural   | water |
     | highway   | residential |
     | aerialway | station |
     | aeroway   | way |
     | boundary  | administrative |
     | craft     | butcher |
     | leisure   | playground |
     | office    | bookmaker |
     | railway   | rail |
     | shop      | bookshop |
     | waterway  | stream |
     | landuse   | cemetry |
     | man_made  | tower |
     | mountain_pass | yes |

    Scenario Outline: Bridges and Tunnels take special name tags
        When loading osm data
         """
         n1 Thighway=road,<key>=yes,name=Rd,<key>:name=My
         n2 Thighway=road,<key>=yes,name=Rd
         """
        Then place contains
          | object     | type | name |
          | N1:highway | road | 'name' : 'Rd' |
          | N1:<key>   | yes  | 'name' : 'My' |
          | N2:highway | road | 'name' : 'Rd' |
        And place has no entry for N2:<key>

    Examples:
      | key |
      | bridge |
      | tunnel |

    Scenario Outline: Excluded places
        When loading osm data
         """
         n1 T<key>=<value>,name=real
         n2 Thighway=motorway,name=To%20%Hell
         """
        Then place has no entry for N1

    Examples:
     | key       | value |
     | emergency | yes |
     | emergency | no |
     | tourism   | yes |
     | tourism   | no |
     | historic  | yes |
     | historic  | no |
     | military  | yes |
     | military  | no |
     | natural   | yes |
     | natural   | no |
     | highway   | no |
     | highway   | turning_circle |
     | highway   | mini_roundabout |
     | highway   | noexit |
     | highway   | crossing |
     | aerialway | no |
     | aerialway | pylon |
     | man_made  | survey_point |
     | man_made  | cutline |
     | aeroway   | no |
     | amenity   | no |
     | bridge    | no |
     | craft     | no |
     | leisure   | no |
     | office    | no |
     | railway   | no |
     | railway   | level_crossing |
     | shop      | no |
     | tunnel    | no |
     | waterway  | riverbank |

    Scenario Outline: Some tags only are included when named
        When loading osm data
        """
        n1 T<key>=<value>
        n2 T<key>=<value>,name=To%20%Hell
        n3 T<key>=<value>,ref=123
        """
        Then place contains exactly
         | object | class | type |
         | N2     | <key> | <value> |

    Examples:
      | key      | value |
      | landuse  | residential |
      | natural  | meadow |
      | highway  | traffic_signals |
      | highway  | service |
      | highway  | cycleway |
      | highway  | path |
      | highway  | footway |
      | highway  | steps |
      | highway  | bridleway |
      | highway  | track |
      | highway  | byway |
      | highway  | motorway_link |
      | highway  | primary_link |
      | highway  | trunk_link |
      | highway  | secondary_link |
      | highway  | tertiary_link |
      | railway  | rail |
      | boundary | administrative |
      | waterway | stream |

    Scenario: named junctions are included if there is no other tag
        When loading osm data
          """
          n1 Tjunction=yes
          n2 Thighway=secondary,junction=roundabout,name=To-Hell
          n3 Tjunction=yes,name=Le%20%Croix
          """
        Then place has no entry for N1
        And place has no entry for N2:junction
        And place contains
         | object | class    | type |
         | N3     | junction | yes |

    Scenario: Boundary with place tag
        When loading osm data
          """
          n200 x0 y0
          n201 x0 y1
          n202 x1 y1
          n203 x1 y0
          w2 Tboundary=administrative,place=city,name=Foo Nn200,n201,n202,n203,n200
          w4 Tboundary=administrative,place=island,name=Foo Nn200,n201,n202,n203,n200
          w20 Tplace=city,name=ngng Nn200,n201,n202,n203,n200
          w40 Tplace=city,boundary=statistical,name=BB Nn200,n201,n202,n203,n200
          """
        Then place contains
          | object       | class    | extratags        | type |
          | W2           | boundary | 'place' : 'city' | administrative |
          | W4:boundary  | boundary | -                | administrative |
          | W4:place     | place    | -                | island |
          | W20          | place    | -                | city |
          | W40:boundary | boundary | -                | statistical |
          | W40:place    | place    | -                | city |
        And place has no entry for W2:place

    Scenario Outline: Tags that describe a house
        When loading osm data
          """
          n100 T<key>=<value>
          n999 Tamenity=prison,<key>=<value>
          """
        Then place contains exactly
          | object | class   | type |
          | N100   | place   | house |
          | N999   | amenity | prison |

    Examples:
      | key                     | value |
      | addr:housename          | My%20%Mansion |
      | addr:housenumber        | 456 |
      | addr:conscriptionnumber | 4 |
      | addr:streetnumber       | 4568765 |

    Scenario: Only named with no other interesting tag
        When loading osm data
          """
          n1 Tlanduse=meadow
          n2 Tlanduse=residential,name=important
          n3 Tlanduse=residential,name=important,place=hamlet
          """
        Then place contains
          | object | class   | type |
          | N2     | landuse | residential |
          | N3     | place   | hamlet |
        And place has no entry for N1
        And place has no entry for N3:landuse

    Scenario Outline: Import of postal codes
        When loading osm data
          """
          n10 Thighway=secondary,<key>=<value>
          n11 T<key>=<value>
          """
        Then place contains
          | object | class   | type      | addr+postcode |
          | N10    | highway | secondary | <value> |
          | N11    | place   | postcode  | <value> |
        And place has no entry for N10:place

    Examples:
      | key                 | value |
      | postal_code         | 45736 |
      | postcode            | xxx |
      | addr:postcode    | 564 |
      | tiger:zip_left   | 00011 |
      | tiger:zip_right  | 09123 |

    Scenario: Import of street and place
        When loading osm data
          """
          n10 Tamenity=hospital,addr:street=Foo%20%St
          n20 Tamenity=hospital,addr:place=Foo%20%Town
          """
        Then place contains
          | object | class   | type     | addr+street | addr+place |
          | N10    | amenity | hospital | Foo St      | -        |
          | N20    | amenity | hospital | -           | Foo Town |


    Scenario Outline: Import of country
        When loading osm data
          """
          n10 Tplace=village,<key>=<value>
          """
        Then place contains
          | object | class   | type    | addr+country |
          | N10    | place   | village | <value> |

    Examples:
        | key                  | value |
        | country_code         | us |
        | ISO3166-1            | XX |
        | is_in:country_code   | __ |
        | addr:country         | .. |
        | addr:country_code    | cv |

    Scenario Outline: Ignore country codes with wrong length
        When loading osm data
          """
          n10 Tplace=village,country_code=<value>
          """
        Then place contains
          | object | class   | type    | addr+country |
          | N10    | place   | village | - |

    Examples:
        | value |
        | X |
        | x |
        | ger |
        | dkeufr |
        | d%20%e |

    Scenario: Import of house numbers
        When loading osm data
          """
          n10 Tbuilding=yes,addr:housenumber=4b
          n11 Tbuilding=yes,addr:conscriptionnumber=003
          n12 Tbuilding=yes,addr:streetnumber=2345
          n13 Tbuilding=yes,addr:conscriptionnumber=3,addr:streetnumber=111
          """
        Then place contains
          | object | class | type    | address |
          | N10    | building | yes  | 'housenumber' : '4b' |
          | N11    | building | yes  | 'conscriptionnumber' : '003' |
          | N12    | building | yes  | 'streetnumber' : '2345' |
          | N13    | building | yes  | 'conscriptionnumber' : '3', 'streetnumber' : '111' |

    Scenario: Shorten tiger:county tags
        When loading osm data
          """
          n10 Tplace=village,tiger:county=Feebourgh%2c%%20%AL
          n11 Tplace=village,addr:state=Alabama,tiger:county=Feebourgh%2c%%20%AL
          n12 Tplace=village,tiger:county=Feebourgh
          """
        Then place contains
          | object | class   | type    | addr+tiger:county |
          | N10    | place   | village | Feebourgh county |
          | N11    | place   | village | Feebourgh county |
          | N12    | place   | village | Feebourgh county |

    Scenario Outline: Import of address tags
        When loading osm data
          """
          n10 Tplace=village,addr:<key>=<value>
          n11 Tplace=village,is_in:<key>=<value>
          """
        Then place contains
          | object | class   | type    | address |
          | N10    | place   | village | '<key>' : '<value>' |

    Examples:
      | key       | value |
      | suburb    | hinein |
      | city      | Sydney |
      | state     | Jura |

    Scenario: Import of isin tags with space
        When loading osm data
          """
          n10 Tplace=village,is_in=Stockholm%2c%%20%Sweden
          n11 Tplace=village,addr:county=le%20%havre
          """
        Then place contains
          | object | class   | type    | address |
          | N10    | place   | village | 'is_in' : 'Stockholm, Sweden' |
          | N11    | place   | village | 'county' : 'le havre' |

    Scenario: Import of admin level
        When loading osm data
          """
          n10 Tamenity=hospital,admin_level=3
          n11 Tamenity=hospital,admin_level=b
          n12 Tamenity=hospital
          n13 Tamenity=hospital,admin_level=3.0
          """
        Then place contains
          | object | class   | type     | admin_level |
          | N10    | amenity | hospital | 3 |
          | N11    | amenity | hospital | 15 |
          | N12    | amenity | hospital | 15 |
          | N13    | amenity | hospital | 3 |

    Scenario Outline: Import of extra tags
        When loading osm data
          """
          n10 Ttourism=hotel,<key>=foo
          """
        Then place contains
          | object | class   | type  | extratags |
          | N10    | tourism | hotel | '<key>' : 'foo' |

     Examples:
       | key |
       | tracktype |
       | traffic_calming |
       | service |
       | cuisine |
       | capital |
       | dispensing |
       | religion |
       | denomination |
       | sport |
       | internet_access |
       | lanes |
       | surface |
       | smoothness |
       | width |
       | est_width |
       | incline |
       | opening_hours |
       | collection_times |
       | service_times |
       | disused |
       | wheelchair |
       | sac_scale |
       | trail_visibility |
       | mtb:scale |
       | mtb:description |
       | wood |
       | drive_in |
       | access |
       | vehicle |
       | bicyle |
       | foot |
       | goods |
       | hgv |
       | motor_vehicle |
       | motor_car |
       | access:foot |
       | contact:phone |
       | drink:mate |
       | oneway |
       | date_on |
       | date_off |
       | day_on |
       | day_off |
       | hour_on |
       | hour_off |
       | maxweight |
       | maxheight |
       | maxspeed |
       | disused |
       | toll |
       | charge |
       | population |
       | description |
       | image |
       | attribution |
       | fax |
       | email |
       | url |
       | website |
       | phone |
       | real_ale |
       | smoking |
       | food |
       | camera |
       | brewery |
       | locality |
       | wikipedia |
       | wikipedia:de |
       | wikidata |
       | name:prefix |
       | name:botanical |
       | name:etymology:wikidata |

    Scenario: buildings
        When loading osm data
          """
          n10 Ttourism=hotel,building=yes
          n11 Tbuilding=house
          n12 Tbuilding=shed,addr:housenumber=1
          n13 Tbuilding=yes,name=Das-Haus
          n14 Tbuilding=yes,addr:postcode=12345
          """
        Then place contains
          | object | class   | type |
          | N10    | tourism | hotel |
          | N12    | building| shed |
          | N13    | building| yes |
          | N14    | place   | postcode |
        And place has no entry for N10:building
        And place has no entry for N11

    Scenario: complete node entry
        When loading osm data
          """
          n290393920 Taddr:city=Perpignan,addr:country=FR,addr:housenumber=43\,addr:postcode=66000,addr:street=Rue%20%Pierre%20%Constant%20%d`Ivry,source=cadastre-dgi-fr%20%source%20%:%20%Direction%20%Générale%20%des%20%Impôts%20%-%20%Cadastre%20%;%20%mise%20%à%20%jour%20%:2008
          """
        Then place contains
         | object     | class   | type | address |
         | N290393920 | place   | house| 'city' : 'Perpignan', 'country' : 'FR', 'housenumber' : '43\\', 'postcode' : '66000', 'street' : 'Rue Pierre Constant d`Ivry' |

    Scenario: odd interpolation
        When loading osm data
          """
          n4 Taddr:housenumber=3 x0 y0
          n5 Taddr:housenumber=15 x0 y0.00001
          w12 Taddr:interpolation=odd Nn4,n5
          w13 Taddr:interpolation=even Nn4,n5
          w14 Taddr:interpolation=-3 Nn4,n5
          """
        Then place contains
            | object | class | type | address |
            | N4     | place | house | 'housenumber' : '3' |
            | N5     | place | house | 'housenumber' : '15' |
            | W12    | place | houses | 'interpolation' : 'odd' |
            | W13    | place | houses | 'interpolation' : 'even' |
            | W14    | place | houses | 'interpolation' : '-3' |

@DB
Feature: Import with custom styles by osm2pgsql
    Tests for the example customizations given in the documentation.

    Scenario: Custom main tags (set new ones)
        Given the lua style file
            """
            local flex = require('import-full')

            flex.set_main_tags{
                boundary = {administrative = 'named'},
                highway = {'always', street_lamp = 'named'},
                landuse = 'fallback'
            }
            """
        When loading osm data
            """
            n10 Tboundary=administrative x0 y0
            n11 Tboundary=administrative,name=Foo x0 y0
            n12 Tboundary=electoral x0 y0
            n13 Thighway=primary x0 y0
            n14 Thighway=street_lamp x0 y0
            n15 Thighway=primary,landuse=street x0 y0
            """
        Then place contains exactly
            | object | class    | type           |
            | N11    | boundary | administrative |
            | N13    | highway  | primary        |
            | N15    | highway  | primary        |

    Scenario: Custom main tags (modify existing)
        Given the lua style file
            """
            local flex = require('import-full')

            flex.add_main_tags{
                amenity = {prison = 'delete'},
                highway = {stop = 'named'},
                aeroway = 'named'
            }
            """
        When loading osm data
            """
            n10 Tamenity=hotel x0 y0
            n11 Tamenity=prison x0 y0
            n12 Thighway=stop x0 y0
            n13 Thighway=stop,name=BigStop x0 y0
            n14 Thighway=give_way x0 y0
            n15 Thighway=bus_stop x0 y0
            n16 Taeroway=no,name=foo x0 y0
            n17 Taeroway=taxiway,name=D15 x0 y0
            """
        Then place contains exactly
            | object | class   | type     |
            | N10    | amenity | hotel    |
            | N13    | highway | stop     |
            | N15    | highway | bus_stop |
            | N17    | aeroway | taxiway  |

    Scenario: Prefiltering tags
        Given the lua style file
            """
            local flex = require('import-full')

            flex.set_prefilters{
                delete_keys = {'source', 'source:*'},
                extra_tags = {amenity = {'yes', 'no'}}
            }
            flex.set_main_tags{
                amenity = 'always',
                tourism = 'always'
            }
            """
        When loading osm data
            """
            n1 Tamenity=yes x0 y6
            n2 Tamenity=hospital,source=survey x3 y6
            n3 Ttourism=hotel,amenity=yes x0 y0
            n4 Ttourism=hotel,amenity=telephone x0 y0
            """
        Then place contains exactly
            | object     | extratags              |
            | N2:amenity | -                      |
            | N3:tourism | 'amenity': 'yes'       |
            | N4:tourism | - |
            | N4:amenity | - |

    Scenario: Ignore some tags
        Given the lua style file
            """
            local flex = require('import-extratags')

            flex.ignore_keys{'ref:*', 'surface'}
            """
        When loading osm data
            """
            n100 Thighway=residential,ref=34,ref:bodo=34,surface=gray,extra=1 x0 y0
            """
        Then place contains exactly
            | object | name         | extratags    |
            | N100   | 'ref' : '34' | 'extra': '1' |


    Scenario: Add for extratags
        Given the lua style file
            """
            local flex = require('import-full')

            flex.add_for_extratags{'ref:*', 'surface'}
            """
        When loading osm data
            """
            n100 Thighway=residential,ref=34,ref:bodo=34,surface=gray,extra=1 x0 y0
            """
        Then place contains exactly
            | object | name         | extratags    |
            | N100   | 'ref' : '34' | 'ref:bodo': '34', 'surface': 'gray' |


    Scenario: Name tags
        Given the lua style file
            """
            local flex = require('flex-base')

            flex.set_main_tags{highway = {traffic_light = 'named'}}
            flex.set_name_tags{main = {'name', 'name:*'},
                               extra = {'ref'}
                              }
            """
        When loading osm data
            """
            n1 Thighway=stop,name=Something x0 y0
            n2 Thighway=traffic_light,ref=453-4 x0 y0
            n3 Thighway=traffic_light,name=Greens x0 y0
            n4 Thighway=traffic_light,name=Red,ref=45 x0 y0
            """
        Then place contains exactly
            | object     | name                       |
            | N3:highway | 'name': 'Greens'           |
            | N4:highway | 'name': 'Red', 'ref': '45' |

    Scenario: Modify name tags
        Given the lua style file
            """
            local flex = require('import-full')

            flex.modify_name_tags{house = {}, extra = {'o'}}
            """
        When loading osm data
            """
            n1 Ttourism=hotel,ref=45,o=good
            n2 Taddr:housename=Old,addr:street=Away
            """
        Then place contains exactly
            | object     | name        |
            | N1:tourism | 'o': 'good' |

    Scenario: Address tags
        Given the lua style file
            """
            local flex = require('import-full')

            flex.set_address_tags{
                main = {'addr:housenumber'},
                extra = {'addr:*'},
                postcode = {'postal_code', 'postcode', 'addr:postcode'},
                country = {'country-code', 'ISO3166-1'}
            }
            """
        When loading osm data
            """
            n1 Ttourism=hotel,addr:street=Foo x0 y0
            n2 Taddr:housenumber=23,addr:street=Budd,postal_code=5567 x0 y0
            n3 Taddr:street=None,addr:city=Where x0 y0
            """
        Then place contains exactly
            | object     | type  | address |
            | N1:tourism | hotel | 'street': 'Foo' |
            | N2:place   | house | 'housenumber': '23', 'street': 'Budd', 'postcode': '5567' |

    Scenario: Modify address tags
        Given the lua style file
            """
            local flex = require('import-full')

            flex.set_address_tags{
                extra = {'addr:*'},
            }
            """
        When loading osm data
            """
            n2 Taddr:housenumber=23,addr:street=Budd,is_in:city=Faraway,postal_code=5567 x0 y0
            """
        Then place contains exactly
            | object     | type  | address |
            | N2:place   | house | 'housenumber': '23', 'street': 'Budd', 'postcode': '5567' |

    Scenario: Unused handling (delete)
        Given the lua style file
            """
            local flex = require('import-full')

            flex.set_address_tags{
                main = {'addr:housenumber'},
                extra = {'addr:*', 'tiger:county'}
            }
            flex.set_unused_handling{delete_keys = {'tiger:*'}}
            """
        When loading osm data
            """
            n1 Ttourism=hotel,tiger:county=Fargo x0 y0
            n2 Ttourism=hotel,tiger:xxd=56,else=other x0 y0
            """
        Then place contains exactly
            | object     | type  | address                 | extratags        |
            | N1:tourism | hotel | 'tiger:county': 'Fargo' | -                |
            | N2:tourism | hotel | -                       | 'else': 'other'  |

    Scenario: Unused handling (extra)
        Given the lua style file
            """
            local flex = require('flex-base')
            flex.set_main_tags{highway = 'always',
                               wikipedia = 'extra'}
            flex.add_for_extratags{'wikipedia:*', 'wikidata'}
            flex.set_unused_handling{extra_keys = {'surface'}}
            """
        When loading osm data
            """
            n100 Thighway=path,foo=bar,wikipedia=en:Path x0 y0
            n234 Thighway=path,surface=rough x0 y0
            n445 Thighway=path,name=something x0 y0
            n446 Thighway=path,wikipedia:en=Path,wikidata=Q23 x0 y0
            n567 Thighway=path,surface=dirt,wikipedia:en=Path x0 y0
            """
        Then place contains exactly
            | object       | type  | extratags              |
            | N100:highway | path  | 'wikipedia': 'en:Path' |
            | N234:highway | path  | 'surface': 'rough' |
            | N445:highway | path  | - |
            | N446:highway | path  | 'wikipedia:en': 'Path', 'wikidata': 'Q23' |
            | N567:highway | path  | 'surface': 'dirt', 'wikipedia:en': 'Path' |

    Scenario: Additional relation types
        Given the lua style file
            """
            local flex = require('import-full')

            flex.RELATION_TYPES['site'] = flex.relation_as_multipolygon
            """
        And the grid
            | 1 | 2 |
            | 4 | 3 |
        When loading osm data
            """
            n1
            n2
            n3
            n4
            w1 Nn1,n2,n3,n4,n1
            r1 Ttype=multipolygon,amenity=school Mw1@
            r2 Ttype=site,amenity=school Mw1@
            """
        Then place contains exactly
            | object     | type   |
            | R1:amenity | school |
            | R2:amenity | school |

    Scenario: Exclude country relations
        Given the lua style file
            """
            local flex = require('import-full')

            function osm2pgsql.process_relation(object)
                if object.tags.boundary ~= 'administrative' or object.tags.admin_level ~= '2' then
                  flex.process_relation(object)
                end
            end
            """
       And the grid
            | 1 | 2 |
            | 4 | 3 |
       When loading osm data
            """
            n1
            n2
            n3
            n4
            w1 Nn1,n2,n3,n4,n1
            r1 Ttype=multipolygon,boundary=administrative,admin_level=4,name=Small Mw1@
            r2 Ttype=multipolygon,boundary=administrative,admin_level=2,name=Big Mw1@
            """
        Then place contains exactly
            | object      | type           |
            | R1:boundary | administrative |

    Scenario: Customize processing functions
        Given the lua style file
            """
            local flex = require('import-full')

            local original_process_tags = flex.process_tags

            function flex.process_tags(o)
                if o.object.tags.highway ~= nil and o.object.tags.access == 'no' then
                    return
                end

                original_process_tags(o)
            end
            """
        When loading osm data
            """
            n1 Thighway=residential x0 y0
            n2 Thighway=residential,access=no x0 y0
            """
        Then place contains exactly
            | object     | type        |
            | N1:highway | residential |

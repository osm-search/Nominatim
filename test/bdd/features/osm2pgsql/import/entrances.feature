Feature: Import of entrance objects by osm2pgsql
    Testing of correct setup of the entrance table

    Scenario: Import simple entrance
        When loading osm data
          """
          n1 Tshop=sweets,entrance=yes,access=public x4.5 y-4
          n2 Trouting:entrance=main x66.1 y0.1
          n3 Tentrance=main,routing:entrance=foot x1 y2
          n4 Thighway=bus_stop
          """
        Then place contains exactly
          | object | class   | type   |
          | N1     | shop    | sweets |
          | N4     | highway | bus_stop |
        And place_entrance contains exactly
          | osm_id | type | extratags!dict                       | geometry!wkt |
          | 1      | yes  | 'shop': 'sweets', 'access': 'public' | 4.5 -4       |
          | 2      | main | -                                    | 66.1 0.1     |
          | 3      | main | -                                    | 1 2          |

    Scenario: Addresses and entrance information can exist on the same node
        When loading osm data
          """
          n1 Taddr:housenumber=10,addr:street=North,entrance=main
          """
          Then place contains exactly
            | object | class | type  | address+housenumber |
            | N1     | place | house | 10                  |
          And place_entrance contains exactly
            | osm_id | type |
            | 1      | main |
    Scenario Outline: Entrance import can be disabled
        Given the lua style file
            """
            local flex = require('import-full')
            flex.set_entrance_filter<param>
            """
        When loading osm data
          """
          n1 Tentrance=yes,access=public
          n2 Trouting:entrance=main
          """
        Then place contains exactly
          | object |
        And place_entrance contains exactly
          | osm_id |

        Examples:
          | param |
          | ()    |
          | (nil) |
          | {}    |
          | {include={'access'}} |
          | {main_tags={}}       |

    Scenario: Entrance import can have custom main tags
        Given the lua style file
            """
            local flex = require('import-full')
            flex.set_entrance_filter{main_tags = {'door'}}
            """
        When loading osm data
          """
          n1 Tentrance=yes,access=public
          n2 Tdoor=foot,entrance=yes
          """
        Then place contains exactly
          | object |
        And place_entrance contains exactly
          | osm_id | type | extratags!dict    |
          | 2      | foot | 'entrance': 'yes' |

    Scenario: Entrance import can have custom extra tags included
        Given the lua style file
            """
            local flex = require('import-full')
            flex.set_entrance_filter{main_tags = {'entrance'},
                                     extra_include = {'access'}}
            """
        When loading osm data
          """
          n1 Tentrance=yes,access=public,shop=newspaper
          n2 Tentrance=yes,shop=sweets
          """
        Then place_entrance contains exactly
          | osm_id | type | extratags!dict     |
          | 1      | yes  | 'access': 'public' |
          | 2      | yes  | -                  |

    Scenario: Entrance import can have custom extra tags excluded
        Given the lua style file
            """
            local flex = require('import-full')
            flex.set_entrance_filter{main_tags = {'entrance', 'door'},
                                     extra_exclude = {'shop'}}
            """
        When loading osm data
          """
          n1 Tentrance=yes,access=public,shop=newspaper
          n2 Tentrance=yes,door=yes,shop=sweets
          """
        Then place_entrance contains exactly
          | osm_id | type | extratags!dict     |
          | 1      | yes  | 'access': 'public' |
          | 2      | yes  | -                  |

    Scenario: Entrance import can have a custom function
        Given the lua style file
            """
            local flex = require('import-full')
            flex.set_entrance_filter{func = function(object)
                return {entrance='always', extratags = {ref = '1'}}
            end}
            """
        When loading osm data
          """
          n1 Tentrance=yes,access=public,shop=newspaper
          n2 Tshop=sweets
          """
        Then place_entrance contains exactly
          | osm_id | type   | extratags!dict     |
          | 1      | always | 'ref': '1'         |
          | 2      | always | 'ref': '1'         |

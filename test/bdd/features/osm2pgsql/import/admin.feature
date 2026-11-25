Feature: Import of place and admin objects
    Testing correct import of features reelvant for the address context

    Scenario: Administrative boundary trumps place trumps any other main tag
        Given the grid
            | 1 | 2 |
            | 4 | 3 |
        When loading osm data
            """
            n1 Tplace=city,amenity=parking,private=yes,name=Foo
            n2 Tplace=suburb,landuse=residential,name=Bar
            n3 Thistoric=castle,place=hamlet,name=So
            n4
            w1 Tboundary=administrative,place=city,name=Foo,admin_level=10 Nn1,n2,n3,n4,n1
            w2 Tboundary=administrative,amenity=prison,name=Foo,admin_level=10 Nn1,n2,n3,n4,n1
            w3 Tlanduse=industrial,boundary=administrative,name=Foo,admin_level=10 Nn1,n2,n3,n4,n1
            """
        Then place contains exactly
            | object | class    | type           | categories!set                                  |
            | N1     | place    | city           | 'osm.place.city', 'osm.amenity.parking'         |
            | N2     | place    | suburb         | 'osm.place.suburb', 'osm.landuse.residential'   |
            | N3     | place    | hamlet         | 'osm.place.hamlet', 'osm.historic.castle'       |
            | W1     | boundary | administrative | 'osm.boundary.administrative', 'osm.place.city' |
            | W2     | boundary | administrative | 'osm.boundary.administrative', 'osm.amenity.prison' |
            | W3     | boundary | administrative | 'osm.boundary.administrative', 'osm.landuse.industrial' |


    Scenario Outline: Tags used by Nominatim internally are always imported
        Given the lua style file
            """
            local flex = require('import-<style>')
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
            n12 Tplace=hamlet,wikidata=Q1234321,name=Bar
            w1 Tboundary=administrative,place=city,name=Foo,wikipedia:de=Foo,admin_level=10 Nn1,n2,n3,n4,n1
            """
        Then place contains exactly
           | object | class    | extratags!dict                         | categories!set                                  |
           | W1     | boundary | 'place': 'city', 'wikipedia:de': 'Foo' | 'osm.boundary.administrative', 'osm.place.city' |
           | N12    | place    | 'wikidata': 'Q1234321'                 | 'osm.place.hamlet'                              |

        Examples:
           | style   |
           | admin   |
           | street  |
           | address |
           | full    |
           | extratags |


    Scenario: Admin levels
        When loading osm data
            """
            n9001 Tplace=city
            n9002 Tplace=city,admin_level=16
            n9003 Tplace=city,admin_level=x
            n9004 Tplace=city,admin_level=1
            n9005 Tplace=city,admin_level=0
            n9006 Tplace=city,admin_level=2.5
            """
        Then place contains exactly
            | object | class | admin_level |
            | N9001  | place | 15          |
            | N9002  | place | 15          |
            | N9003  | place | 15          |
            | N9004  | place | 1           |
            | N9005  | place | 15          |
            | N9006  | place | 15          |


    Scenario: Administrative boundaries only as areas
        Given the grid
            | 1 | 2 |
            | 4 | 3 |
        When loading osm data
            """
            n1
            n2
            n3
            n4
            w100 Tboundary=administrative,name=A,admin_level=8 Nn1,n2,n3
            w101 Tboundary=administrative,name=A,admin_level=8 Nn1,n4,n3
            w200 Tboundary=administrative,name=B,admin_level=5 Nn1,n2,n3,n4,n1
            w201 Tboundary=administrative,name=C,admin_level=10 Nn1,n2,n3,n4,n1
            r100 Ttype=boundary,boundary=administrative,name=A,admin_level=8 Mw100@,w101@
            r101 Ttype=boundary,boundary=administrative,admin_level=4 Mw100@,w101@
            """
        Then place contains exactly
            | object |
            | W201   |
            | R100   |


    Scenario: Administrative boundaries with place tags
        Given the grid
            | 1 | 2 |
            | 3 |   |
        When loading osm data
            """
            n1
            n2
            n3
            w10001 Tboundary=administrative,place=city,name=A,admin_level=10 Nn1,n2,n3,n1
            w10002 Tboundary=natural,place=city,name=B Nn1,n2,n3,n1
            w10003 Tboundary=administrative,place=island,name=C,admin_level=10 Nn1,n2,n3,n1
            """
        Then place contains
            | object | class    | type           | categories!set                                    |
            | W10001 | boundary | administrative | 'osm.boundary.administrative', 'osm.place.city'   |
            | W10002 | place    | city           | 'osm.boundary.natural', 'osm.place.city'          |
            | W10003 | boundary | administrative | 'osm.boundary.administrative', 'osm.place.island' |


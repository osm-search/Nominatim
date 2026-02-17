Feature: Import of interpolations
    Test if interpolation objects are correctly imported into the
    place_interpolation table

    Background:
        Given the grid
            | 1 | 2 |
            | 4 | 3 |

    Scenario: Simple address interpolations
        When loading osm data
            """
            n1
            n2
            w13001 Taddr:interpolation=odd,addr:street=Blumenstrasse Nn1,n2
            w13002 Taddr:interpolation=even,place=city Nn1,n2
            w13003 Taddr:interpolation=odd Nn1,n1
            """
        Then place contains exactly
            | object | class | type |
            | W13002 | place | city |
        And place_interpolation contains exactly
            | object | type | address!dict              | nodes!ints | geometry!wkt |
            | W13001 | odd  | "street": "Blumenstrasse" | 1,2        | 1,2          |
            | W13002 | even | -                         | 1,2        | 1,2          |

    Scenario: Address interpolation with housenumber
        When loading osm data
            """
            n1
            n2
            n3
            n4
            w34 Taddr:interpolation=all,addr:housenumber=2-4,building=yes Nn1,n2,n3,n4,n1
            w35 Taddr:interpolation=all,addr:housenumber=5,building=yes Nn1,n2,n3,n4,n1
            w36 Taddr:interpolation=all,addr:housenumber=2a-c,building=yes Nn1,n2,n3,n4,n1
            """
        Then place contains exactly
            | object | class    | type | address!dict                                |
            | w35    | building | yes  | "housenumber" : "5", "interpolation": "all" |
            | w36    | building | yes  | "housenumber" : "2a-c", "interpolation": "all" |
        Then place_interpolation contains exactly
            | object | type | address!dict         | nodes!ints | geometry!wkt |
            | W34    | all  | "housenumber": "2-4" | -          | (1,2,3,4,1)  |

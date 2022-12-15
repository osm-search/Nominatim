@DB
Feature: Tag evaluation
    Tests if tags are correctly imported into the place table

    Scenario: Main tags as fallback
        When loading osm data
            """
            n100 Tjunction=yes,highway=bus_stop
            n101 Tjunction=yes,name=Bar
            n200 Tbuilding=yes,amenity=cafe
            n201 Tbuilding=yes,name=Intersting
            n202 Tbuilding=yes
            """
        Then place contains exactly
            | object | class    | type     |
            | N100   | highway  | bus_stop |
            | N101   | junction | yes      |
            | N200   | amenity  | cafe     |
            | N201   | building | yes      |


    Scenario: Name and reg tags
        When loading osm data
            """
            n2001 Thighway=road,name=Foo,alt_name:de=Bar,ref=45
            n2002 Thighway=road,name:prefix=Pre,name:suffix=Post,ref:de=55
            n2003 Thighway=yes,name:%20%de=Foo,name=real1
            n2004 Thighway=yes,name:%a%de=Foo,name=real2
            n2005 Thighway=yes,name:%9%de=Foo,name:\\=real3
            n2006 Thighway=yes,name:%9%de=Foo,name=rea\l3
            """
        Then place contains exactly
            | object | class   | type | name |
            | N2001  | highway | road | 'name': 'Foo', 'alt_name:de': 'Bar', 'ref': '45' |
            | N2002  | highway | road | - |
            | N2003  | highway | yes  | 'name: de': 'Foo', 'name': 'real1' |
            | N2004  | highway | yes  | 'name:\nde': 'Foo', 'name': 'real2' |
            | N2005  | highway | yes  | 'name:\tde': 'Foo', 'name:\\\\': 'real3' |
            | N2006  | highway | yes  | 'name:\tde': 'Foo', 'name': 'rea\\l3' |

        And place contains
            | object | extratags |
            | N2002  | 'name:prefix': 'Pre', 'name:suffix': 'Post', 'ref:de': '55' |


    Scenario: Name when using with_name flag
        When loading osm data
            """
            n3001 Tbridge=yes,bridge:name=GoldenGate
            n3002 Tbridge=yes,bridge:name:en=Rainbow
            """
        Then place contains exactly
            | object | class   | type | name                 |
            | N3001  | bridge  | yes  | 'name': 'GoldenGate' |
            | N3002  | bridge  | yes  | 'name:en': 'Rainbow' |


    Scenario: Address tags
        When loading osm data
            """
            n4001 Taddr:housenumber=34,addr:city=Esmarald,addr:county=Land
            n4002 Taddr:streetnumber=10,is_in:city=Rootoo,is_in=Gold
            """
        Then place contains exactly
            | object | class | address             |
            | N4001  | place | 'housenumber': '34', 'city': 'Esmarald', 'county': 'Land' |
            | N4002  | place | 'streetnumber': '10', 'city': 'Rootoo' |


    Scenario: Country codes
        When loading osm data
            """
            n5001 Tshop=yes,country_code=DE
            n5002 Tshop=yes,country_code=toolong
            n5003 Tshop=yes,country_code=x
            n5004 Tshop=yes,addr:country=us
            n5005 Tshop=yes,country=be
            n5006 Tshop=yes,addr:country=France
            """
        Then place contains exactly
            | object | class | address         |
            | N5001  | shop  | 'country': 'DE' |
            | N5002  | shop  | - |
            | N5003  | shop  | - |
            | N5004  | shop  | 'country': 'us' |
            | N5005  | shop  | - |
            | N5006  | shop  | - |


    Scenario: Postcodes
        When loading osm data
            """
            n6001 Tshop=bank,addr:postcode=12345
            n6002 Tshop=bank,tiger:zip_left=34343
            n6003 Tshop=bank,is_in:postcode=9009
            """
        Then place contains exactly
            | object | class | address             |
            | N6001  | shop  | 'postcode': '12345' |
            | N6002  | shop  | 'postcode': '34343' |
            | N6003  | shop  | -                   |


    Scenario: Main with extra
        When loading osm data
            """
            n7001 Thighway=primary,bridge=yes,name=1
            n7002 Thighway=primary,bridge=yes,bridge:name=1
            """
        Then place contains exactly
            | object        | class   | type    | name        | extratags+bridge:name |
            | N7001         | highway | primary | 'name': '1' | -                     |
            | N7002:highway | highway | primary | -           | 1                     |
            | N7002:bridge  | bridge  | yes     | 'name': '1' | 1                     |


    Scenario: Global fallback and skipping
        When loading osm data
            """
            n8001 Tshop=shoes,note:de=Nein,xx=yy
            n8002 Tshop=shoes,building=no,ele=234
            n8003 Tshop=shoes,name:source=survey
            """
        Then place contains exactly
            | object | class | name | extratags    |
            | N8001  | shop  |  -   | 'xx': 'yy'   |
            | N8002  | shop  |  -   | 'ele': '234' |
            | N8003  | shop  |  -   | -            |


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


    Scenario: Administrative boundaries with place tags
        When loading osm data
            """
            n10001 Tboundary=administrative,place=city,name=A
            n10002 Tboundary=natural,place=city,name=B
            n10003 Tboundary=administrative,place=island,name=C
            """
        Then place contains
            | object          | class    | type           | extratags       |
            | N10001          | boundary | administrative | 'place': 'city' |
        And place contains
            | object          | class    | type           |
            | N10002:boundary | boundary | natural        |
            | N10002:place    | place    | city           |
            | N10003:boundary | boundary | administrative |
            | N10003:place    | place    | island         |


    Scenario: Building fallbacks
        When loading osm data
            """
            n12001 Ttourism=hotel,building=yes
            n12002 Tbuilding=house
            n12003 Tbuilding=shed,addr:housenumber=1
            n12004 Tbuilding=yes,name=Das-Haus
            n12005 Tbuilding=yes,addr:postcode=12345
            """
        Then place contains exactly
            | object | class    | type     |
            | N12001 | tourism  | hotel    |
            | N12003 | building | shed     |
            | N12004 | building | yes      |
            | N12005 | place    | postcode |


    Scenario: Address interpolations
        When loading osm data
            """
            n13001 Taddr:interpolation=odd
            n13002 Taddr:interpolation=even,place=city
            """
        Then place contains exactly
            | object | class | type   | address                 |
            | N13001 | place | houses | 'interpolation': 'odd'  |
            | N13002 | place | houses | 'interpolation': 'even' |

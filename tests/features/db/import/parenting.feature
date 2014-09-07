@DB
Feature: Parenting of objects
    Tests that the correct parent is choosen

    Scenario: Address inherits postcode from its street unless it has a postcode
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | housenumber | geometry
         | 1      | place | house | 4           | :p-N1
        And the place nodes
         | osm_id | class | type  | housenumber | postcode | geometry
         | 2      | place | house | 5           | 99999    | :p-N1
        And the place ways
         | osm_id | class   | type        | name  | postcode | geometry
         | 1      | highway | residential | galoo | 12345    | :w-north
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1
         | N2     | W1
        When sending query "4 galoo"
        Then results contain
         | ID | osm_type | osm_id | langaddress
         | 0  | N        | 1      | 4, galoo, 12345
        When sending query "5 galoo"
        Then results contain
         | ID | osm_type | osm_id | langaddress
         | 0  | N        | 2      | 5, galoo, 99999


    Scenario: Address without tags, closest street
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | geometry
         | 1      | place | house | :p-N1
         | 2      | place | house | :p-N2
         | 3      | place | house | :p-S1
         | 4      | place | house | :p-S2
        And the named place ways
         | osm_id | class   | type        | geometry
         | 1      | highway | residential | :w-north
         | 2      | highway | residential | :w-south
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1
         | N2     | W1
         | N3     | W2
         | N4     | W2

    Scenario: Address without tags avoids unnamed streets
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | geometry
         | 1      | place | house | :p-N1
         | 2      | place | house | :p-N2
         | 3      | place | house | :p-S1
         | 4      | place | house | :p-S2
        And the place ways
         | osm_id | class   | type        | geometry
         | 1      | highway | residential | :w-north
        And the named place ways
         | osm_id | class   | type        | geometry
         | 2      | highway | residential | :w-south
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W2
         | N2     | W2
         | N3     | W2
         | N4     | W2

    Scenario: addr:street tag parents to appropriately named street
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | street| geometry
         | 1      | place | house | south | :p-N1
         | 2      | place | house | north | :p-N2
         | 3      | place | house | south | :p-S1
         | 4      | place | house | north | :p-S2
        And the place ways
         | osm_id | class   | type        | name  | geometry
         | 1      | highway | residential | north | :w-north
         | 2      | highway | residential | south | :w-south
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W2
         | N2     | W1
         | N3     | W2
         | N4     | W1

    Scenario: addr:street tag parents to next named street
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | street | geometry
         | 1      | place | house | abcdef | :p-N1
         | 2      | place | house | abcdef | :p-N2
         | 3      | place | house | abcdef | :p-S1
         | 4      | place | house | abcdef | :p-S2
        And the place ways
         | osm_id | class   | type        | name   | geometry
         | 1      | highway | residential | abcdef | :w-north
         | 2      | highway | residential | abcdef | :w-south
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1
         | N2     | W1
         | N3     | W2
         | N4     | W2

    Scenario: addr:street tag without appropriately named street
        Given the scene roads-with-pois
        And the place nodes
         | osm_id | class | type  | street | geometry
         | 1      | place | house | abcdef | :p-N1
         | 2      | place | house | abcdef | :p-N2
         | 3      | place | house | abcdef | :p-S1
         | 4      | place | house | abcdef | :p-S2
        And the place ways
         | osm_id | class   | type        | name  | geometry
         | 1      | highway | residential | abcde | :w-north
         | 2      | highway | residential | abcde | :w-south
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1
         | N2     | W1
         | N3     | W2
         | N4     | W2

    Scenario: addr:place address
        Given the scene road-with-alley
        And the place nodes
         | osm_id | class | type   | addr_place | geometry
         | 1      | place | house  | myhamlet   | :n-alley
        And the place nodes
         | osm_id | class | type   | name     | geometry
         | 2      | place | hamlet | myhamlet | :n-main-west
        And the place ways
         | osm_id | class   | type        | name     | geometry
         | 1      | highway | residential | myhamlet | :w-main
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | N2

    Scenario: addr:street is preferred over addr:place
        Given the scene road-with-alley
        And the place nodes
         | osm_id | class | type   | addr_place | street  | geometry
         | 1      | place | house  | myhamlet   | mystreet| :n-alley
        And the place nodes
         | osm_id | class | type   | name     | geometry
         | 2      | place | hamlet | myhamlet | :n-main-west
        And the place ways
         | osm_id | class   | type        | name     | geometry
         | 1      | highway | residential | mystreet | :w-main
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1

     Scenario: Untagged address in simple associated street relation
        Given the scene road-with-alley
        And the place nodes
         | osm_id | class | type  | geometry
         | 1      | place | house | :n-alley
         | 2      | place | house | :n-corner
         | 3      | place | house | :n-main-west
        And the place ways
         | osm_id | class   | type        | name | geometry
         | 1      | highway | residential | foo  | :w-main
         | 2      | highway | service     | bar  | :w-alley
        And the relations
         | id | members            | tags
         | 1  | W1:street,N1,N2,N3 | 'type' : 'associatedStreet'
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1
         | N2     | W1
         | N3     | W1
         
    Scenario: Avoid unnamed streets in simple associated street relation
        Given the scene road-with-alley
        And the place nodes
         | osm_id | class | type  | geometry
         | 1      | place | house | :n-alley
         | 2      | place | house | :n-corner
         | 3      | place | house | :n-main-west
        And the named place ways
         | osm_id | class   | type        | geometry
         | 1      | highway | residential | :w-main
        And the place ways
         | osm_id | class   | type        | geometry
         | 2      | highway | residential | :w-alley
        And the relations
         | id | members            | tags
         | 1  | N1,N2,N3,W2:street,W1:street | 'type' : 'associatedStreet'
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1
         | N2     | W1
         | N3     | W1

    ### Scenario 10
    Scenario: Associated street relation overrides addr:street
        Given the scene road-with-alley
        And the place nodes
         | osm_id | class | type  | street | geometry
         | 1      | place | house | bar    | :n-alley
        And the place ways
         | osm_id | class   | type        | name | geometry
         | 1      | highway | residential | foo  | :w-main
         | 2      | highway | residential | bar  | :w-alley
        And the relations
         | id | members            | tags
         | 1  | W1:street,N1,N2,N3 | 'type' : 'associatedStreet'
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W1

    Scenario: Building without tags, closest street from center point
        Given the scene building-on-street-corner
        And the named place ways
         | osm_id | class    | type        | geometry
         | 1      | building | yes         | :w-building
         | 2      | highway  | primary     | :w-WE
         | 3      | highway  | residential | :w-NS
        When importing
        Then table placex contains
         | object | parent_place_id
         | W1     | W3

    Scenario: Building with addr:street tags
        Given the scene building-on-street-corner
        And the named place ways
         | osm_id | class    | type | street | geometry
         | 1      | building | yes  | bar    | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        When importing
        Then table placex contains
         | object | parent_place_id
         | W1     | W2

    Scenario: Building with addr:place tags
        Given the scene building-on-street-corner
        And the place nodes
         | osm_id | class | type    | name | geometry
         | 1      | place | village | bar  | :n-outer
        And the named place ways
         | osm_id | class    | type | addr_place | geometry
         | 1      | building | yes  | bar        | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        When importing
        Then table placex contains
         | object | parent_place_id
         | W1     | N1

    Scenario: Building in associated street relation
        Given the scene building-on-street-corner
        And the named place ways
         | osm_id | class    | type | geometry
         | 1      | building | yes  | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        And the relations
         | id | members            | tags
         | 1  | W1:house,W2:street | 'type' : 'associatedStreet'
        When importing
        Then table placex contains
         | object | parent_place_id
         | W1     | W2

    Scenario: Building in associated street relation overrides addr:street
        Given the scene building-on-street-corner
        And the named place ways
         | osm_id | class    | type | street | geometry
         | 1      | building | yes  | foo    | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        And the relations
         | id | members            | tags
         | 1  | W1:house,W2:street | 'type' : 'associatedStreet'
        When importing
        Then table placex contains
         | object | parent_place_id
         | W1     | W2

    Scenario: Wrong member in associated street relation is ignored
        Given the scene building-on-street-corner
        And the named place nodes
         | osm_id | class | type  | geometry
         | 1      | place | house | :n-outer
        And the named place ways
         | osm_id | class    | type | street | geometry
         | 1      | building | yes  | foo    | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        And the relations
         | id | members                      | tags
         | 1  | N1:house,W1:street,W3:street | 'type' : 'associatedStreet'
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W3

    Scenario: POIs in building inherit address
        Given the scene building-on-street-corner
        And the named place nodes
         | osm_id | class   | type       | geometry
         | 1      | amenity | bank       | :n-inner
         | 2      | shop    | bakery     | :n-edge-NS
         | 3      | shop    | supermarket| :n-edge-WE
        And the place ways
         | osm_id | class    | type | street | addr_place | housenumber | geometry
         | 1      | building | yes  | foo    | nowhere    | 3           | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        When importing
        Then table placex contains
         | object | parent_place_id | street | addr_place | housenumber
         | W1     | W3              | foo    | nowhere    | 3
         | N1     | W3              | foo    | nowhere    | 3
         | N2     | W3              | foo    | nowhere    | 3
         | N3     | W3              | foo    | nowhere    | 3

    Scenario: POIs don't inherit from streets
        Given the scene building-on-street-corner
        And the named place nodes
         | osm_id | class   | type       | geometry
         | 1      | amenity | bank       | :n-inner
        And the place ways
         | osm_id | class    | type | street | addr_place | housenumber | geometry
         | 1      | highway  | path | foo    | nowhere    | 3           | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 3      | highway  | residential | foo  | :w-NS
        When importing
        Then table placex contains
         | object | parent_place_id | street | addr_place | housenumber
         | N1     | W3              | None   | None       | None

    Scenario: POIs with own address do not inherit building address
        Given the scene building-on-street-corner
        And the named place nodes
         | osm_id | class   | type       | street | geometry
         | 1      | amenity | bank       | bar    | :n-inner
        And the named place nodes
         | osm_id | class   | type       | housenumber | geometry
         | 2      | shop    | bakery     | 4           | :n-edge-NS
        And the named place nodes
         | osm_id | class   | type       | addr_place  | geometry
         | 3      | shop    | supermarket| nowhere     | :n-edge-WE
        And the place nodes
         | osm_id | class | type              | name     | geometry
         | 4      | place | isolated_dwelling | theplace | :n-outer
        And the place ways
         | osm_id | class    | type | addr_place | housenumber | geometry
         | 1      | building | yes  | theplace   | 3           | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        When importing
        Then table placex contains
         | object | parent_place_id | street | addr_place | housenumber
         | W1     | N4              | None   | theplace   | 3
         | N1     | W2              | bar    | None       | None
         | N2     | W3              | None   | None       | 4
         | N3     | W2              | None   | nowhere    | None

    ### Scenario 20
    Scenario: POIs parent a road if and only if they are attached to it
        Given the scene points-on-roads
        And the named place nodes
         | osm_id | class   | type     | street   | geometry
         | 1      | highway | bus_stop | North St | :n-SE
         | 2      | highway | bus_stop | South St | :n-NW
         | 3      | highway | bus_stop | North St | :n-S-unglued
         | 4      | highway | bus_stop | South St | :n-N-unglued
        And the place ways
         | osm_id | class   | type         | name     | geometry
         | 1      | highway | secondary    | North St | :w-north
         | 2      | highway | unclassified | South St | :w-south
        And the ways
         | id | nodes
         | 1  | 100,101,2,103,104
         | 2  | 200,201,1,202,203
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W2
         | N2     | W1
         | N3     | W1
         | N4     | W2

    Scenario: POIs do not parent non-roads they are attached to
        Given the scene points-on-roads
        And the named place nodes
         | osm_id | class   | type     | street   | geometry
         | 1      | highway | bus_stop | North St | :n-SE
         | 2      | highway | bus_stop | South St | :n-NW
        And the place ways
         | osm_id | class   | type         | name     | geometry
         | 1      | landuse | residential  | North St | :w-north
         | 2      | waterway| river        | South St | :w-south
        And the ways
         | id | nodes
         | 1  | 100,101,2,103,104
         | 2  | 200,201,1,202,203
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | 0
         | N2     | 0

    Scenario: POIs on building outlines inherit associated street relation
        Given the scene building-on-street-corner
        And the named place nodes
         | osm_id | class  | type  | geometry
         | 1      | place  | house | :n-edge-NS
        And the named place ways
         | osm_id | class    | type | geometry
         | 1      | building | yes  | :w-building
        And the place ways
         | osm_id | class    | type        | name | geometry
         | 2      | highway  | primary     | bar  | :w-WE
         | 3      | highway  | residential | foo  | :w-NS
        And the relations
         | id | members            | tags
         | 1  | W1:house,W2:street | 'type' : 'associatedStreet'
        And the ways
         | id | nodes
         | 1  | 100,1,101,102,100
        When importing
        Then table placex contains
         | object | parent_place_id
         | N1     | W2


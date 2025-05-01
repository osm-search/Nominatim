Feature: Country handling
    Tests for import and use of country information

    Scenario: Country names from OSM country relations are added
        Given the places
            | osm  | class    | type           | admin | name+name:xy | country | geometry |
            | R1   | boundary | administrative | 2     | Loudou       | de      | (9 52, 9 53, 10 52, 9 52) |
        Given the places
            | osm  | class    | type          | name  | geometry   |
            | N1   | place    | town          | Wenig | country:de |
        When importing
        When geocoding "Wenig, Loudou"
        Then the result set contains
            | object | display_name |
            | N1     | Wenig, Deutschland |
        When geocoding "Wenig"
            | accept-language |
            | xy,en |
        Then the result set contains
            | object | display_name |
            | N1     | Wenig, Loudou |

    Scenario: OSM country relations outside expected boundaries are ignored for naming
        Given the grid
            | 1 |  | 2 |
            | 4 |  | 3 |
        Given the places
            | osm  | class    | type           | admin | name+name:xy | country | geometry |
            | R1   | boundary | administrative | 2     | Loudou       | de      | (1,2,3,4,1) |
        Given the places
            | osm  | class    | type          | name  | geometry   |
            | N1   | place    | town          | Wenig | country:de |
        When importing
        When geocoding "Wenig"
            | accept-language |
            | xy,en |
        Then the result set contains
            | object | display_name |
            | N1     | Wenig, Germany |

    Scenario: Pre-defined country names are used
        Given the grid with origin CH
            | 1 |
        Given the places
            | osm  | class    | type          | name  | geometry   |
            | N1   | place    | town          | Ingb  | 1          |
        When importing
        And geocoding "Ingb"
            | accept-language |
            | en,de |
        Then the result set contains
            | object | display_name |
            | N1     | Ingb, Switzerland |

    Scenario: For overlapping countries, pre-defined countries are tie-breakers
        Given the grid with origin US
            | 1 |   | 2 |   | 5 |
            |   | 9 |   | 8 |   |
            | 4 |   | 3 |   | 6 |
        Given the named places
            | osm  | class    | type           | admin | country | geometry |
            | R1   | boundary | administrative | 2     | de      | (1,5,6,4,1) |
            | R2   | boundary | administrative | 2     | us      | (1,2,3,4,1) |
        And the named places
            | osm  | class    | type  | geometry   |
            | N1   | place    | town  | 9 |
            | N2   | place    | town  | 8 |
        When importing
        Then placex contains
            | object | country_code |
            | N1     | us           |
            | N2     | de           |

    Scenario: For overlapping countries outside pre-define countries prefer smaller partition
        Given the grid with origin US
            | 1 |   | 2 |   | 5 |
            |   | 9 |   | 8 |   |
            | 4 |   | 3 |   | 6 |
        Given the named places
            | osm  | class    | type           | admin | country | geometry |
            | R1   | boundary | administrative | 2     | ch      | (1,5,6,4,1) |
            | R2   | boundary | administrative | 2     | de      | (1,2,3,4,1) |
        And the named places
            | osm  | class    | type  | geometry   |
            | N1   | place    | town  | 9 |
            | N2   | place    | town  | 8 |
        When importing
        Then placex contains
            | object | country_code |
            | N1     | de           |
            | N2     | ch           |

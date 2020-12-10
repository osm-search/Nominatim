@DB
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
        When searching for "Wenig, Loudou"
        Then results contain
            | osm_type | osm_id | name |
            | N        | 1      | Wenig, Deutschland |
        When searching for "Wenig"
            | accept-language |
            | xy,en |
        Then results contain
            | osm_type | osm_id | name |
            | N        | 1      | Wenig, Loudou |
    Scenario: OSM country relations outside expected boundaries are ignored
        Given the places
            | osm  | class    | type           | admin | name+name:xy | country | geometry |
            | R1   | boundary | administrative | 2     | Loudou       | de      | poly-area:0.1 |
        Given the places
            | osm  | class    | type          | name  | geometry   |
            | N1   | place    | town          | Wenig | country:de |
        When importing
        When searching for "Wenig"
            | accept-language |
            | xy,en |
        Then results contain
            | osm_type | osm_id | name |
            | N        | 1      | Wenig, Germany |
    Scenario: Pre-defined country names are used
        Given the places
            | osm  | class    | type          | name  | geometry   |
            | N1   | place    | town          | Ingb  | country:ch |
        When importing
        And searching for "Ingb"
            | accept-language |
            | en,de |
        Then results contain
            | osm_type | osm_id | name |
            | N        | 1      | Ingb, Switzerland |

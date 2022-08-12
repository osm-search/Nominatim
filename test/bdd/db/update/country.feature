@DB
Feature: Country handling
    Tests for update of country information

    Background:
        Given the 1.0 grid with origin DE
            | 1 |    | 2 |
            |   | 10 |   |
            | 4 |    | 3 |

    @fail-legacy
    Scenario: When country names are changed old ones are no longer searchable
        Given the places
            | osm | class    | type           | admin | name+name:xy | country | geometry |
            | R1  | boundary | administrative | 2     | Loudou       | de      | (1,2,3,4,1) |
        Given the places
            | osm | class    | type          | name  |
            | N10 | place    | town          | Wenig |
        When importing
        When sending search query "Wenig, Loudou"
        Then results contain
            | osm |
            | N10 |
        When updating places
            | osm | class    | type           | admin | name+name:xy | country | geometry |
            | R1  | boundary | administrative | 2     | Germany      | de      | (1,2,3,4,1) |
        When sending search query "Wenig, Loudou"
        Then exactly 0 results are returned

    @fail-legacy
    Scenario: When country names are deleted they are no longer searchable
        Given the places
            | osm | class    | type           | admin | name+name:xy | country | geometry |
            | R1  | boundary | administrative | 2     | Loudou       | de      | (1,2,3,4,1) |
        Given the places
            | osm | class    | type          | name  |
            | N10 | place    | town          | Wenig |
        When importing
        When sending search query "Wenig, Loudou"
        Then results contain
            | osm |
            | N10 |
        When updating places
            | osm | class    | type           | admin | name+name:en | country | geometry |
            | R1  | boundary | administrative | 2     | Germany      | de      | (1,2,3,4,1) |
        When sending search query "Wenig, Loudou"
        Then exactly 0 results are returned
        When sending search query "Wenig"
            | accept-language |
            | xy,en |
        Then results contain
            | osm | display_name |
            | N10 | Wenig, Germany |


    Scenario: Default country names are always searchable
        Given the places
            | osm | class    | type          | name  |
            | N10 | place    | town          | Wenig |
        When importing
        When sending search query "Wenig, Germany"
        Then results contain
            | osm |
            | N10 |
        When sending search query "Wenig, de"
        Then results contain
            | osm |
            | N10 |
        When updating places
            | osm  | class    | type           | admin | name+name:en | country | geometry |
            | R1   | boundary | administrative | 2     | Lilly        | de      | (1,2,3,4,1) |
        When sending search query "Wenig, Germany"
            | accept-language |
            | en,de |
        Then results contain
            | osm | display_name |
            | N10 | Wenig, Lilly |
        When sending search query "Wenig, de"
            | accept-language |
            | en,de |
        Then results contain
            | osm | display_name |
            | N10 | Wenig, Lilly |


    @fail-legacy
    Scenario: When a localised name is deleted, the standard name takes over
        Given the places
            | osm | class    | type           | admin | name+name:de | country | geometry |
            | R1  | boundary | administrative | 2     | Loudou       | de      | (1,2,3,4,1) |
        Given the places
            | osm | class    | type          | name  |
            | N10 | place    | town          | Wenig |
        When importing
        When sending search query "Wenig, Loudou"
            | accept-language |
            | de,en |
        Then results contain
            | osm | display_name |
            | N10 | Wenig, Loudou |
        When updating places
            | osm | class    | type           | admin | name+name:en | country | geometry |
            | R1  | boundary | administrative | 2     | Germany      | de      | (1,2,3,4,1) |
        When sending search query "Wenig, Loudou"
        Then exactly 0 results are returned
        When sending search query "Wenig"
            | accept-language |
            | de,en |
        Then results contain
            | osm | display_name |
            | N10 | Wenig, Deutschland |


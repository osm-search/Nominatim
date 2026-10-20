Feature: Searches in the UK
    Test addressing particularities in the UK.

    Scenario: A terrace address tagged with addr:place with a parent street is found
        Given the grid with origin GB
          | 10 |   |   |   |   | 11 |
          |    | 1 |   |   | 2 |    |
          |    |   | 8 | 9 |   |    |
          | 13 |   |   |   |   | 12 |
        And the places
          | osm | class   | type        | name       | geometry |
          | W1  | highway | residential | Garden Way | 1,2      |
          | W10 | place   | suburb      | Lille      | (10,11,12,13,10) |
        And the places
          | osm | class | type  | housenr | street     | geometry |
          | N8  | place | house | 5       | Garden Way | 8 |
        And the places
          | osm | class | type  | housenr | addr+place  | addr+parentstreet | geometry |
          | N9  | place | house | 5       | Bow Terrace | Garden Way        | 9        |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N8     | W1              |
          | N9     | W10             |
        When geocoding "5 Garden Way, Lille"
        Then all results contain
          | object | display_name!fm |
          | N8     | 5, Garden Way, Lille,.* |
        When geocoding "5 Bow Terrace, Garden Way"
        Then all results contain
          | object | display_name!fm |
          | N9     | 5, Bow Terrace, Garden Way, Lille,.* |

    Scenario: A landuse address tagged with addr:place with a parent street is found
        Given the grid with origin GB
          | 10 |   |   |   |   | 11 |
          |    | 1 |   |   | 2 |    |
          |    |   | 8 | 9 |   |    |
          | 13 |   |   |   |   | 12 |
        And the places
          | osm | class   | type        | name       | geometry |
          | W1  | highway | residential | Garden Way | 1,2      |
          | W9  | landuse | industrial  | IArea      | (10,11,12,13,10) |
          | W10 | place   | suburb      | Lille      | (10,11,12,13,10) |
        And the places
          | osm | class | type  | housenr | street     | geometry |
          | N8  | place | house | 5       | Garden Way | 8 |
        And the places
          | osm | class | type  | housenr | addr+place  | addr+parentstreet | geometry |
          | N9  | place | house | 5       | IArea       | Garden Way        | 9        |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N8     | W1              |
          | N9     | W9              |
        When geocoding "5 Garden Way, Lille"
        Then all results contain
          | object | display_name!fm |
          | N8     | 5, Garden Way, IArea, Lille,.* |
        When geocoding "5 IArea, Garden Way"
        Then all results contain
          | object | display_name!fm |
          | N9     | 5, IArea, Garden Way, Lille,.* |

    Scenario: A dependent street address is found
        Given the grid with origin GB
          | 10 |   |   |   |   | 11 |
          |    | 1 |   | 4 | 2 |    |
          |    |   | 8 |   |   |    |
          |    |   |   | 5 |   |    |
          |    |   |   | 9 |   |    |
          | 13 |   |   |   |   | 12 |
        And the places
          | osm | class   | type        | name       | geometry |
          | W1  | highway | residential | Garden Way | 1,4,2 |
          | W2  | highway | residential | Short Road | 4,5 |
          | W10 | place   | suburb      | Lille      | (10,11,12,13,10) |
        And the places
          | osm | class | type  | housenr | street     | geometry |
          | N8  | place | house | 5       | Garden Way | 8 |
        And the places
          | osm | class | type  | housenr | addr+street | addr+parentstreet | geometry |
          | N9  | place | house | 5       | Short Road  | Garden Way        | 9        |
        When importing
        Then placex contains
          | object | parent_place_id |
          | N8     | W1              |
          | N9     | W2              |
        When geocoding "5 Garden Way, Lille"
        Then all results contain
          | object | display_name!fm |
          | N8     | 5, Garden Way, Lille,.* |
        When geocoding "5 Short Road, Garden Way"
        Then all results contain
          | object | display_name!fm |
          | N9     | 5, Short Road, Garden Way, Lille,.* |

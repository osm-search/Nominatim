@DB
Feature: Searching of simple objects
    Testing simple stuff

    Scenario: Search for place node
        Given the places
          | osm | class | type    | name+name | geometry   |
          | N1  | place | village | Foo       | 10.0 -10.0 |
        When importing
        And searching for "Foo"
        Then results contain
         | ID | osm | class | type    | centroid |
         | 0  | N1  | place | village | 10 -10   |

     Scenario: Updating postcode in postcode boundaries without ref
        Given the places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 12345    | poly-area:1.0 |
        When importing
        And searching for "12345"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | R        | 1 |
        When updating places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 54321    | poly-area:1.0 |
        And searching for "12345"
        Then results contain
         | osm_type |
         | P        |
        When searching for "54321"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | R        | 1 |

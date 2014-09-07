@DB
Feature: Update of names in place objects
    Test all naming related issues in updates


    Scenario: Updating postcode in postcode boundaries without ref
        Given the place areas
          | osm_type | osm_id | class    | type        | postcode | geometry
          | R        | 1      | boundary | postal_code | 12345    | (0 0, 1 0, 1 1, 0 1, 0 0)
        When importing
        And sending query "12345"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | R        | 1
        When updating place areas
          | osm_type | osm_id | class    | type        | postcode | geometry
          | R        | 1      | boundary | postal_code | 54321    | (0 0, 1 0, 1 1, 0 1, 0 0)
        And sending query "12345"
        Then exactly 0 results are returned
        When sending query "54321"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | R        | 1


    Scenario: Delete postcode from postcode boundaries without ref
        Given the place areas
          | osm_type | osm_id | class    | type        | postcode | geometry
          | R        | 1      | boundary | postal_code | 12345    | (0 0, 1 0, 1 1, 0 1, 0 0)
        When importing
        And sending query "12345"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | R        | 1
        When updating place areas
          | osm_type | osm_id | class    | type        | geometry
          | R        | 1      | boundary | postal_code | (0 0, 1 0, 1 1, 0 1, 0 0)
        Then table placex has no entry for R1


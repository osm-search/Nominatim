@DB
Feature: Update of names in place objects
    Test all naming related issues in updates

    Scenario: Delete postcode from postcode boundaries without ref
        Given the grid with origin DE
          | 1 | 2 |
          | 4 | 3 |
        Given the places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 12345    | (1,2,3,4,1) |
        When importing
        And sending search query "12345"
        Then results contain
         | ID | osm |
         | 0  | R1 |
        When updating places
          | osm | class    | type        | geometry |
          | R1  | boundary | postal_code | (1,2,3,4,1) |
        Then placex has no entry for R1


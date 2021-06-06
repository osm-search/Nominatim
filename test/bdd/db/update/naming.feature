@DB
Feature: Update of names in place objects
    Test all naming related issues in updates

    Scenario: Delete postcode from postcode boundaries without ref
        Given the places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 12345    | poly-area:0.5 |
        When importing
        And sending search query "12345"
        Then results contain
         | ID | osm |
         | 0  | R1 |
        When updating places
          | osm | class    | type        | geometry |
          | R1  | boundary | postal_code | poly-area:0.5 |
        Then placex has no entry for R1


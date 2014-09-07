Feature: Structured search queries
    Testing correctness of results with
    structured queries

    Scenario: Country only
        When sending json structured query with address
          | country
          | Canada
        Then address of result 0 is
          | type         | value
          | country      | Canada
          | country_code | ca

    Scenario: Postcode only
        When sending json structured query with address
          | postalcode
          | 22547
        Then at least 1 result is returned 
        And results contain
          | type
          | post(al_)?code
        And result addresses contain
          | postcode
          | 22547


    Scenario: Street, postcode and country
        When sending xml structured query with address
          | street          | postalcode | country
          | Old Palace Road | GU2 7UP    | United Kingdom
        Then at least 1 result is returned
        Then result header contains
          | attr        | value
          | querystring | Old Palace Road, GU2 7UP, United Kingdom


    Scenario: gihub #176
        When sending json structured query with address
          | city
          | Washington
        Then at least 1 result is returned

@UNKNOWNDB
Feature: Status queries against unknown database
    Testing status query

    Scenario: Failed status as text
        When sending text status query
        Then a HTTP 500 is returned
        And the page contents equals "ERROR: No database"

    Scenario: Failed status as json
        When sending json status query
        Then a HTTP 200 is returned
        And the result is valid json
        And results contain
          | status | message |
          | 700    | No database |
        And result has not attributes data_updated

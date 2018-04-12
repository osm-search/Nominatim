@APIDB
Feature: Status queries
    Testing status query

    Scenario: Status as text
        When sending status query
        Then a HTTP 200 is returned
        And the page contents equals "OK"

    Scenario: Failed status as text
        When sending text status query demanding error
        Then a HTTP 500 is returned
        And the page contents equals "ERROR: An Error"


    Scenario: Status as json
        When sending json status query
        Then the result is valid json
        And results contain
          | status | message |
          | 0      | OK      |
        And result has attributes data_updated

    Scenario: Failed status as json
        When sending json status query demanding error
        Then a HTTP 200 is returned
        And the result is valid json
        And results contain
          | status | message |
          | 799    | An Error |
        And result has not attributes data_updated

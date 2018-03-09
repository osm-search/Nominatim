@APIDB
Feature: Status queries
    Testing status query

    Scenario: Status as text
        When sending status query
        Then a HTTP 200 is returned
        And the page contents equals "OK"

    Scenario: Status as json
        When sending json status query
        Then the result is valid json
        And results contain
          | status | code | message |
          | ok     | 200  | OK      |
        And result has attributes data_updated

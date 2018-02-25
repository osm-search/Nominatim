@APIDB
Feature: Status queries
    Testing status query

    Scenario: Status as text
        When sending status query
        Then a HTTP 500 is returned
        And the page contents equals "ERROR: No database"

    Scenario: Status as json
        When sending json status query
        Then a HTTP 500 is returned
        And the page contents equals "{"status":"error","code":500,"message":"No database"}"

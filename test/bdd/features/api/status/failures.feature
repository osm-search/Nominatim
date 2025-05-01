Feature: Status queries against unknown database
    Testing status query

    Background:
        Given an unknown database

    Scenario: Failed status as text
        When sending v1/status
        Then a HTTP 500 is returned
        And the page content equals "ERROR: Database connection failed"

    Scenario: Failed status as json
        When sending v1/status with format json
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | status!:d | message |
          | 700       | Database connection failed |
        And the result has no attributes data_updated

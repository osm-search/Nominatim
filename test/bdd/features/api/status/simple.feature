Feature: Status queries
    Testing status query

    Scenario: Status as text
        When sending v1/status
        Then a HTTP 200 is returned
        And the page content equals "OK"

    Scenario: Status as json
        When sending v1/status with format json
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | status!:d | message | data_updated!fm |
          | 0         | OK      | ....-..-..T..:..:...00:00 |

@APIDB
Feature: Object details
    Check details page for correctness

    Scenario Outline: Details via OSM id
        When sending <format> details query for <object>
        Then the result is valid <format>

    Examples:
     | format | object |
     | json | 107077 |
     | json | N5484325405 |
     | json | W43327921 |
     | json | R123924 |

    Scenario Outline: Details via unknown OSM id
        When sending <format> details query for <object>
        Then a HTTP 400 is returned

    Examples:
      | format | object |
      | json | 1 |
      | json | R1 |

    Scenario: Details with keywords
        When sending details query for W43327921
            | keywords |
            | 1 |
        Then the result is valid json

    # ticket #1343
    Scenario: Details of a country with keywords
        When sending details query for R1155955
            | keywords |
            | 1 |
        Then the result is valid json


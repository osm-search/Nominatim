@APIDB
Feature: Object details
    Check details page for correctness

    Scenario Outline: Details via OSM id
        When sending <format> details query for <object>
        Then the result is valid <format>

    Examples:
     | format | object |
     | html | 492887 |
     | json | 492887 |
     | html | N4267356889 |
     | json | N4267356889 |
     | html | W230804120 |
     | json | W230804120 |
     | html | R123924 |
     | json | R123924 |

    Scenario Outline: Details via unknown OSM id
        When sending <format> details query for <object>
        Then a HTTP 400 is returned

    Examples:
      | format | object |
      | html | 1 |
      | json | 1 |
      | html | R1 |
      | json | R1 |

    Scenario: Details with keywords
        When sending details query for W78099902
            | keywords |
            | 1 |
        Then the result is valid html


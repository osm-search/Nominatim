@APIDB
Feature: Object details
    Check details page for correctness

    Scenario Outline: Details via OSM id
        When sending details query for <object>
        Then the result is valid html

    Examples:
     | object |
     | 492887 |
     | N4267356889 |
     | W230804120 |
     | R123924 |

    Scenario: Details with keywords
        When sending details query for W78099902
            | keywords |
            | 1 |
        Then the result is valid html

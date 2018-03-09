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

    Scenario: JSON Details
        When sending json details query for W78099902
        Then the result is valid json
        And result has not attributes place_search_name_keywords,place_search_address_keywords,address_lines,linked_lines,parentof_lines

    Scenario: JSON Details with keywords
        When sending json details query for W78099902
            | keywords |
            | 1 |
        Then the result is valid json
        And result has attributes place_search_name_keywords,place_search_address_keywords

    Scenario: JSON Details with addressdetails
        When sending json details query for W78099902
            | addressdetails |
            | 1 |
        Then the result is valid json
        And result has attributes address_lines

    Scenario: JSON Details with linkedplaces
        When sending json details query for R123924
            | linkedplaces |
            | 1 |
        Then the result is valid json
        And result has attributes linked_lines

    Scenario: JSON Details with childplaces
        When sending json details query for W78099902
            | childplaces |
            | 1 |
        Then the result is valid json
        And result has attributes parentof_lines

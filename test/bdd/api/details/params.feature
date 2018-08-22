@APIDB
Feature: Object details
    Testing different parameter options for details API.

    Scenario: JSON Details
        When sending json details query for W78099902
        Then the result is valid json
        And result has attributes geometry
        And result has not attributes keywords,address,linked_places,parentof

    Scenario: JSON Details with keywords
        When sending json details query for W78099902
            | keywords |
            | 1 |
        Then the result is valid json
        And result has attributes keywords

    Scenario: JSON Details with addressdetails
        When sending json details query for W78099902
            | addressdetails |
            | 1 |
        Then the result is valid json
        And result has attributes address

    Scenario: JSON Details with linkedplaces
        When sending json details query for R123924
            | linkedplaces |
            | 1 |
        Then the result is valid json
        And result has attributes linked_places

    Scenario: JSON Details with hierarchy
        When sending json details query for W78099902
            | hierarchy |
            | 1 |
        Then the result is valid json
        And result has attributes hierarchy

    Scenario: JSON Details with linkedplaces
        When sending json details query for R123924
            | linkedplaces |
            | 1 |
        Then the result is valid json

    Scenario Outline: HTML Details with keywords
        When sending html details query for <osmid>
            | keywords |
            | 1 |
        Then the result is valid html

    Examples:
            | osmid |
            | W78099902 |
            | N3121929846 |



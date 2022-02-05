@DB
Feature: Searching of house numbers
    Test for specialised treeatment of housenumbers

    Background:
        Given the grid
         | 1 |   | 2 |   | 3 |
         |   | 9 |   |   |   |
         |   |   |   |   | 4 |


    Scenario: A simple numeral housenumber is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | 45      | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | North Road | 1,2,3    |
        When importing
        And sending search query "45, North Road"
        Then results contain
         | osm |
         | N1  |
        When sending search query "North Road 45"
        Then results contain
         | osm |
         | N1  |


    Scenario Outline: Each housenumber in a list is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnrs>  | 9        |
        And the places
         | osm | class   | type | name     | geometry |
         | W10 | highway | path | Multistr | 1,2,3    |
        When importing
        When sending search query "2 Multistr"
        Then results contain
         | osm |
         | N1  |
        When sending search query "4 Multistr"
        Then results contain
         | osm |
         | N1  |
        When sending search query "12 Multistr"
        Then results contain
         | osm |
         | N1  |

     Examples:
        | hnrs |
        | 2;4;12 |
        | 2,4,12 |
        | 2, 4, 12 |


    Scenario: A name mapped as a housenumber is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | Warring | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | Chester St | 1,2,3    |
        When importing
        When sending search query "Chester St Warring"
        Then results contain
         | osm |
         | N1  |

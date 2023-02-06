@APIDB
Feature: Object details
    Check details page for correctness

    Scenario: Details by place ID
        When sending details query for 107077
        Then the result is valid json
        And results contain
            | place_id |
            | 107077   |


    Scenario Outline: Details via OSM id
        When sending details query for <type><id>
        Then the result is valid json
        And results contain
            | osm_type | osm_id |
            | <type>   | <id> |

    Examples:
     | type | id |
     | N    | 5484325405 |
     | W    | 43327921 |
     | R    | 123924 |


    Scenario Outline: Details for different class types for the same OSM id
        When sending details query for N300209696:<class>
        Then the result is valid json
        And results contain
          | osm_type | osm_id    | category |
          | N        | 300209696 | <class> |

    Examples:
     | class |
     | tourism |
     | natural |
     | mountain_pass |


    Scenario Outline: Details via unknown OSM id
        When sending details query for <object>
        Then a HTTP 404 is returned

    Examples:
      | object |
      | 1 |
      | R1 |
      | N300209696:highway |


    @v1-api-php-only
    Scenario: Details for interpolation way just return the dependent street
        When sending details query for W1
        Then the result is valid json
        And results contain
            | category |
            | highway |


     @v1-api-python-only
     Scenario: Details for interpolation way return the interpolation
        When sending details query for W1
        Then the result is valid json
        And results contain
            | category | type   | osm_type | osm_id | admin_level |
            | place    | houses | W        | 1      | 15          |


    @v1-api-php-only
     Scenario: Details for Tiger way just return the dependent street
        When sending details query for 112871
        Then the result is valid json
        And results contain
            | category |
            | highway |


     @v1-api-python-only
     Scenario: Details for interpolation way return the interpolation
        When sending details query for 112871
        Then the result is valid json
        And results contain
            | category | type   | admin_level |
            | place    | houses | 15          |
        And result has not attributes osm_type,osm_id


    @v1-api-php-only
     Scenario: Details for postcodes just return the dependent place
        When sending details query for 112820
        Then the result is valid json
        And results contain
            | category |
            | boundary |


     @v1-api-python-only
     Scenario: Details for interpolation way return the interpolation
        When sending details query for 112820
        Then the result is valid json
        And results contain
            | category | type     | admin_level |
            | place    | postcode | 15          |
        And result has not attributes osm_type,osm_id

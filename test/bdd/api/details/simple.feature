@SQLITE
@APIDB
Feature: Object details
    Check details page for correctness

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


     Scenario: Details for interpolation way return the interpolation
        When sending details query for W1
        Then the result is valid json
        And results contain
            | category | type   | osm_type | osm_id | admin_level |
            | place    | houses | W        | 1      | 15          |


     @Fail
     Scenario: Details for interpolation way return the interpolation
        When sending details query for 112871
        Then the result is valid json
        And results contain
            | category | type   | admin_level |
            | place    | houses | 15          |
        And result has not attributes osm_type,osm_id


     @Fail
     Scenario: Details for interpolation way return the interpolation
        When sending details query for 112820
        Then the result is valid json
        And results contain
            | category | type     | admin_level |
            | place    | postcode | 15          |
        And result has not attributes osm_type,osm_id


    Scenario Outline: Details debug output returns no errors
        When sending debug details query for <feature>
        Then the result is valid html

        Examples:
          | feature     |
          | N5484325405 |
          | W1          |
          | 112820      |
          | 112871      |

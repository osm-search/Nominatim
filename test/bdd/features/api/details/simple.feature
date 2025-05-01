Feature: Object details
    Check details page for correctness

    Scenario Outline: Details request with OSM id
        When sending v1/details
          | osmtype | osmid |
          | <type>  | <id>  |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
            | osm_type | osm_id |
            | <type>   | <id> |

    Examples:
     | type | id |
     | N    | 5484325405 |
     | W    | 43327921 |
     | R    | 123924 |

    Scenario Outline: Details request with different class types for the same OSM id
        When sending v1/details
          | osmtype | osmid     | class   |
          | N       | 300209696 | <class> |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | osm_type | osm_id    | category |
          | N        | 300209696 | <class>  |

    Examples:
     | class |
     | tourism |
     | mountain_pass |

    Scenario: Details request without osmtype
        When sending v1/details
          | osmid |
          | <id>  |
        Then a HTTP 400 is returned
        And the result is valid json

    Scenario: Details request with unknown OSM id
        When sending v1/details
          | osmtype | osmid |
          | R       | 1     |
        Then a HTTP 404 is returned
        And the result is valid json

    Scenario: Details request with unknown class
        When sending v1/details
          | osmtype | osmid     | class   |
          | N       | 300209696 | highway |
        Then a HTTP 404 is returned
        And the result is valid json

    Scenario: Details for interpolation way return the interpolation
        When sending v1/details
          | osmtype | osmid |
          | W       | 1     |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | category | type   | osm_type | osm_id | admin_level |
          | place    | houses | W        | 1      | 15          |


    @skip
    Scenario: Details for interpolation way return the interpolation
        When sending details query for 112871
        Then the result is valid json
        And the result contains
            | category | type   | admin_level |
            | place    | houses | 15          |
        And result has not attributes osm_type,osm_id


    @skip
    Scenario: Details for postcode
        When sending details query for 112820
        Then the result is valid json
        And the result contains
            | category | type     | admin_level |
            | place    | postcode | 15          |
        And result has not attributes osm_type,osm_id


    Scenario Outline: Details debug output returns no errors
        When sending v1/details
          | osmtype | osmid | debug |
          | <type>  | <id>  | 1     |
        Then a HTTP 200 is returned
        And the result is valid html

    Examples:
     | type | id |
     | N    | 5484325405 |
     | W    | 43327921 |
     | R    | 123924 |


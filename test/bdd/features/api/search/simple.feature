Feature: Simple Tests
    Simple tests for internal server errors and response format.

    Scenario Outline: Garbage Searches
        When sending v1/search
          | q |
          | <query> |
        Then a HTTP 200 is returned
        And the result is valid json
        And exactly 0 results are returned

    Examples:
     | query |
     | New York, New York |
     | 12, Main Street, Houston |
     | München |
     | 東京都 |
     | hotels in sdfewf |
     | xywxkrf |
     | gh; foo() |
     | %#$@*&l;der#$! |
     | 234.23.14.5 |
     | aussenstelle universitat lichtenstein wachterhaus aussenstelle universitat lichtenstein wachterhaus aussenstelle universitat lichtenstein wachterhaus aussenstelle universitat lichtenstein wachterhaus |
     | . |

    Scenario: Empty XML search
        When sending v1/search with format xml
          | q        |
          | xnznxvcx |
        Then a HTTP 200 is returned
        And the result is valid xml
        Then the result metadata contains
          | param       | value |
          | querystring | xnznxvcx |
          | more_url!fm | .*q=xnznxvcx.*format=xml |

    Scenario: Empty XML search with special XML characters
        When sending v1/search with format xml
          | q |
          | xfdghn&zxn"xvbyx<vxx>cssdex |
        Then a HTTP 200 is returned
        And the result is valid xml
        Then the result metadata contains
          | param       | value |
          | querystring | xfdghn&zxn"xvbyx<vxx>cssdex |
          | more_url!fm | .*q=xfdghn%26zxn%22xvbyx%3Cvxx%3Ecssdex.*format=xml |

    Scenario: Empty XML search with viewbox
        When sending v1/search with format xml
          | q        | viewbox |
          | xnznxvcx | 12,33,77,45.13 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result metadata contains
          | param        | value |
          | querystring | xnznxvcx |
          | viewbox     | 12,33,77,45.13 |

    Scenario: Empty XML search with viewboxlbrt
        When sending v1/search with format xml
          | q        | viewboxlbrt |
          | xnznxvcx | 12,34.13,77,45 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result metadata contains
          | param       | value |
          | querystring | xnznxvcx |
          | viewbox     | 12,34.13,77,45 |

    Scenario: Empty XML search with viewboxlbrt and viewbox
        When sending v1/search with format xml
          | q   | viewbox        | viewboxblrt |
          | pub | 12,33,77,45.13 | 1,2,3,4 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result metadata contains
          | param       | value |
          | querystring | pub |
          | viewbox     | 12,33,77,45.13 |

    Scenario: Empty XML search with excluded place ids
        When sending v1/search with format xml
          | q              | exclude_place_ids |
          | jghrleoxsbwjer | 123,76,342565 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result metadata contains
          | param             | value |
          | exclude_place_ids | 123,76,342565 |

    Scenario: Empty XML search with bad excluded place ids
        When sending v1/search with format xml
          | q              | exclude_place_ids |
          | jghrleoxsbwjer | , |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result metadata has no attributes exclude_place_ids

    Scenario Outline: Wrapping of illegal jsonp search requests
        When sending v1/search with format json
          | q     | json_callback |
          | Tokyo | <data> |
        Then a HTTP 400 is returned
        And the result is valid json
        And the result contains
          | error+code | error+message |
          | 400        | Invalid json_callback value |

        Examples:
          | data |
          | 1asd |
          | bar(foo) |
          | XXX['bad'] |
          | foo; evil |
          | 234 |

    Scenario: Ignore jsonp parameter for anything but json
        When sending v1/search with format xml
          | q     | json_callback |
          | Tokyo | 234 |
        Then a HTTP 200 is returned
        Then the result is valid xml

    Scenario Outline: Empty search for json like
        When sending v1/search with format <format>
          | q |
          | YHlERzzx |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And exactly 0 results are returned

        Examples:
          | format | outformat |
          | json   | json |
          | jsonv2 | json |
          | geojson | geojson |
          | geocodejson | geocodejson |

    Scenario: Search for non-existing coordinates
        When geocoding "-21.0,-33.0"
        Then exactly 0 results are returned

    Scenario: Country code selection is retained in more URL (#596)
        When sending v1/search with format xml
          | q     | countrycodes |
          | Vaduz | pl,1,,invalid,undefined,%3Cb%3E,bo,, |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result metadata contains
          | more_url!fm |
          | .*&countrycodes=pl%2Cbo&.* |

    Scenario Outline: Search debug output does not return errors
        When sending v1/search
          | q       | debug |
          | <query> | 1     |
        Then a HTTP 200 is returned
        And the result is valid html

        Examples:
          | query |
          | Liechtenstein |
          | Triesen |
          | Pfarrkirche |
          | Landstr 27 Steinort, Triesenberg, 9495 |
          | 9497 |
          | restaurant in triesen |

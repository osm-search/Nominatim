Feature: Simple Tests
    Simple tests for internal server errors and response format.
    These tests should pass on any Nominatim installation.

    Scenario Outline: Testing different parameters
        Given the request parameters
          | <parameter>
          | <value>
        When sending search query "Manchester"
        Then the result is valid html
        Given the request parameters
          | <parameter>
          | <value>
        When sending html search query "Manchester"
        Then the result is valid html
        Given the request parameters
          | <parameter>
          | <value>
        When sending xml search query "Manchester"
        Then the result is valid xml
        Given the request parameters
          | <parameter>
          | <value>
        When sending json search query "Manchester"
        Then the result is valid json
        Given the request parameters
          | <parameter>
          | <value>
        When sending jsonv2 search query "Manchester"
        Then the result is valid json

    Examples:
     | parameter        | value
     | addressdetails   | 1
     | addressdetails   | 0
     | polygon          | 1
     | polygon          | 0
     | polygon_text     | 1
     | polygon_text     | 0
     | polygon_kml      | 1
     | polygon_kml      | 0
     | polygon_geojson  | 1
     | polygon_geojson  | 0
     | polygon_svg      | 1
     | polygon_svg      | 0
     | accept-language  | de,en
     | countrycodes     | uk,ir
     | bounded          | 1
     | bounded          | 0
     | exclude_place_ids| 385252,1234515
     | limit            | 1000
     | dedupe           | 1
     | dedupe           | 0

    Scenario: Search with invalid output format
        Given the request parameters
          | format
          | fd$#
        When sending search query "Berlin"
        Then the result is valid html

    Scenario Outline: Simple Searches
        When sending search query "<query>"
        Then the result is valid html
        When sending html search query "<query>"
        Then the result is valid html
        When sending xml search query "<query>"
        Then the result is valid xml
        When sending json search query "<query>"
        Then the result is valid json
        When sending jsonv2 search query "<query>"
        Then the result is valid json

    Examples:
     | query
     | New York, New York
     | France
     | 12, Main Street, Houston
     | München
     | 東京都
     | hotels in nantes
     | xywxkrf
     | gh; foo()
     | %#$@*&l;der#$!
     | 234
     | 47.4,8.3

    Scenario: Empty XML search
        When sending xml search query "xnznxvcx"
        Then result header contains
          | attr        | value
          | querystring | xnznxvcx
          | polygon     | false
          | more_url    | .*format=xml.*q=xnznxvcx.*

    Scenario: Empty XML search with special XML characters
        When sending xml search query "xfdghn&zxn"xvbyx<vxx>cssdex"
        Then result header contains
          | attr        | value
          | querystring | xfdghn&zxn"xvbyx<vxx>cssdex
          | polygon     | false
          | more_url    | .*format=xml.*q=xfdghn&zxn"xvbyx<vxx>cssdex.*

    Scenario: Empty XML search with viewbox
        Given the request parameters
          | viewbox
          | 12,45.13,77,33
        When sending xml search query "xnznxvcx"
        Then result header contains
          | attr        | value
          | querystring | xnznxvcx
          | polygon     | false
          | viewbox     | 12,45.13,77,33

    Scenario: Empty XML search with viewboxlbrt
        Given the request parameters
          | viewboxlbrt
          | 12,34.13,77,45
        When sending xml search query "xnznxvcx"
        Then result header contains
          | attr        | value
          | querystring | xnznxvcx
          | polygon     | false
          | viewbox     | 12,45.13,77,33

    Scenario: Empty XML search with viewboxlbrt and viewbox
        Given the request parameters
          | viewbox        | viewboxblrt
          | 12,45.13,77,33 | 1,2,3,4
        When sending xml search query "pub"
        Then result header contains
          | attr        | value
          | querystring | pub
          | polygon     | false
          | viewbox     | 12,45.13,77,33


    Scenario Outline: Empty XML search with polygon values
        Given the request parameters
          | polygon
          | <polyval>
        When sending xml search query "xnznxvcx"
        Then result header contains
          | attr        | value
          | polygon     | <result>

    Examples:
     | result | polyval
     | false  | 0
     | true   | 1
     | true   | True
     | true   | true
     | true   | false
     | true   | FALSE
     | true   | yes
     | true   | no
     | true   | '; delete from foobar; select '


    Scenario: Empty XML search with exluded place ids
        Given the request parameters
          | exclude_place_ids
          | 123,76,342565
        When sending xml search query "jghrleoxsbwjer"
        Then result header contains
          | attr              | value
          | exclude_place_ids | 123,76,342565

    Scenario: Empty XML search with bad exluded place ids
        Given the request parameters
          | exclude_place_ids
          | ,
        When sending xml search query "jghrleoxsbwjer"
        Then result header has no attribute exclude_place_ids

    Scenario Outline: Wrapping of legal jsonp search requests
        Given the request parameters
          | json_callback
          | <data>
        When sending json search query "Tokyo"
        Then there is a json wrapper "<data>"

    Examples:
     | data
     | foo
     | FOO
     | __world
     | $me
     | m1[4]
     | d_r[$d]

    Scenario Outline: Wrapping of illegal jsonp search requests
        Given the request parameters
          | json_callback
          | <data>
        When sending json search query "Tokyo"
        Then a HTTP 400 is returned

    Examples:
      | data
      | 1asd
      | bar(foo)
      | XXX['bad']
      | foo; evil

    Scenario Outline: Ignore jsonp parameter for anything but json
        Given the request parameters
          | json_callback
          | 234
        When sending json search query "Malibu"
        Then a HTTP 400 is returned
        Given the request parameters
          | json_callback
          | 234
        When sending xml search query "Malibu"
        Then the result is valid xml
        Given the request parameters
          | json_callback
          | 234
        When sending html search query "Malibu"
        Then the result is valid html

     Scenario: Empty JSON search
        When sending json search query "YHlERzzx"
        Then exactly 0 results are returned

     Scenario: Empty JSONv2 search
        When sending jsonv2 search query "Flubb XdfESSaZx"
        Then exactly 0 results are returned

     Scenario: Search for non-existing coordinates
        When sending json search query "-21.0,-33.0"
        Then exactly 0 results are returned


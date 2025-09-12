Feature: Search API geocodejson output
    Testing correctness of geocodejson output.

    Scenario: Search geocodejson - City housenumber-level address with street
        When sending v1/search with format geocodejson
          | q                    | addressdetails |
          | Im Winkel 8, Triesen | 1 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson
        And all results contain
          | housenumber | street    | postcode | city    | country |
          | 8           | Im Winkel | 9495     | Triesen | Liechtenstein |

    Scenario: Search geocodejson - Town street-level address with street
        When sending v1/search with format geocodejson
          | q                | addressdetails |
          | Gnetsch, Balzers | 1 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson
        And all results contain
          | name    | city    | postcode | country |
          | Gnetsch | Balzers | 9496     | Liechtenstein |

    Scenario: Search geocodejson - Town street-level address with footway
        When sending v1/search with format geocodejson
          | q                     | addressdetails |
          | 6000 jahre geschichte | 1 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson
        And all results contain
          | street  | city    | postcode | country |
          | Burgweg | Balzers | 9496     | Liechtenstein |

    Scenario: Search geocodejson - City address with suburb
        When sending v1/search with format geocodejson
          | q                           | addressdetails |
          | Lochgass 5, Ebenholz, Vaduz | 1 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson
        And all results contain
          | housenumber | street   | district | city  | postcode | country |
          | 5           | Lochgass | Ebenholz | Vaduz | 9490     | Liechtenstein |

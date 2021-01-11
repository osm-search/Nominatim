@APIDB
Feature: Parameters for Search API
    Testing correctness of geocodejson output.

    Scenario: City housenumber-level address with street
        When sending geocodejson search query "Im Winkel 8, Triesen" with address
        Then results contain
          | housenumber | street    | postcode | city    | country |
          | 8           | Im Winkel | 9495     | Triesen | Liechtenstein |

    Scenario: Town street-level address with street
        When sending geocodejson search query "Gnetsch, Balzers" with address
        Then results contain
          | name    | city    | postcode | country |
          | Gnetsch | Balzers | 9496     | Liechtenstein |

    Scenario: Town street-level address with footway
        When sending geocodejson search query "burg gutenberg 6000 jahre geschichte" with address
        Then results contain
          | street  | city    | postcode | country |
          | Burgweg | Balzers | 9496     | Liechtenstein |

    Scenario: City address with suburb
        When sending geocodejson search query "Lochgass 5, Ebenholz, Vaduz" with address
        Then results contain
          | housenumber | street   | district | city  | postcode | country |
          | 5           | Lochgass | Ebenholz | Vaduz | 9490     | Liechtenstein |

@APIDB
Feature: Parameters for Reverse API
    Testing correctness of geocodejson output.

    Scenario: City housenumber-level address with street
        When sending geocodejson reverse coordinates 47.1068011,9.52810091
        Then results contain
          | housenumber | street    | postcode | city    | country |
          | 8           | Im Winkel | 9495     | Triesen | Liechtenstein |

    Scenario: Town street-level address with street
        When sending geocodejson reverse coordinates 47.066,9.504
          | zoom |
          | 16 |
        Then results contain
          | name    | city    | postcode | country |
          | Gnetsch | Balzers | 9496     | Liechtenstein |

    Scenario: Poi street-level address with footway
        When sending geocodejson reverse coordinates 47.0653,9.5007
        Then results contain
          | street  | city    | postcode | country |
          | Burgweg | Balzers | 9496     | Liechtenstein |

    Scenario: City address with suburb
        When sending geocodejson reverse coordinates 47.146861,9.511771
        Then results contain
          | housenumber | street   | district | city  | postcode | country |
          | 5           | Lochgass | Ebenholz | Vaduz | 9490     | Liechtenstein |

@APIDB
Feature: Parameters for Reverse API
    Testing correctness of geocodejson output.

    Scenario: City housenumber-level address with street
        When sending geocodejson reverse coordinates 53.556,9.9607
        Then results contain
          | housenumber | street           | postcode | city    | country |
          | 10          | Brunnenhofstraße | 22767    | Hamburg | Deutschland | 

    Scenario: Town street-level address with street
        When sending geocodejson reverse coordinates 47.066,9.504
        Then results contain
          | street  | city    | postcode | country |
          | Gnetsch | Balzers | 9496     | Liechtenstein |

    Scenario: Town street-level address with footway
        When sending geocodejson reverse coordinates 47.0653,9.5007
        Then results contain
          | street  | city    | postcode | country |
          | Burgweg | Balzers | 9496     | Liechtenstein |

    Scenario: City address with suburb
        When sending geocodejson reverse coordinates 53.5822,10.0805
        Then results contain
          | housenumber | street                | locality  | city    | postcode | country |
          | 64          | Hinschenfelder Straße | Wandsbek  | Hamburg | 22047    | Deutschland |

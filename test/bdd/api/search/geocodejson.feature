@APIDB
Feature: Parameters for Search API
    Testing correctness of geocodejson output.

    Scenario: City housenumber-level address with street
        When sending geocodejson search query "Brunnenhofstr 10, Hamburg" with address
        Then results contain
          | housenumber | street           | postcode | city    | country |
          | 10          | Brunnenhofstraße | 22767    | Hamburg | Deutschland | 

    Scenario: Town street-level address with street
        When sending geocodejson search query "Gnetsch, Balzers" with address
        Then results contain
          | street  | city    | postcode | country |
          | Gnetsch | Balzers | 9496     | Liechtenstein |

    Scenario: Town street-level address with footway
        When sending geocodejson search query "burg gutenberg 6000 jahre geschichte" with address
        Then results contain
          | street  | city    | postcode | country |
          | Burgweg | Balzers | 9496     | Liechtenstein |

    Scenario: City address with suburb
        When sending geocodejson search query "hinschenfelder str 64, wandsbek" with address
        Then results contain
          | housenumber | street                | district | city    | postcode | country |
          | 64          | Hinschenfelder Straße | Wandsbek | Hamburg | 22047    | Deutschland |

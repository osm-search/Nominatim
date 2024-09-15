@SQLITE
@APIDB
Feature: Layer parameter in reverse geocoding
    Testing correct function of layer selection while reverse geocoding

    Scenario: POIs are selected by default
        When sending v1/reverse at 47.14077,9.52414
        Then results contain
          | category | type      |
          | tourism  | viewpoint |


    Scenario Outline: Same address level POI with different layers
        When sending v1/reverse at 47.14077,9.52414
          | layer   |
          | <layer> |
        Then results contain
          | category   |
          | <category> |


        Examples:
          | layer           | category |
          | address         | highway  |
          | poi,address     | tourism  |
          | address,poi     | tourism  |
          | natural         | waterway |
          | address,natural | highway  |
          | natural,poi     | tourism  |


     Scenario Outline: POIs are not selected without housenumber for address layer
        When sending v1/reverse at 47.13816,9.52168
          | layer   |
          | <layer> |
        Then results contain
          | category   | type   |
          | <category> | <type> |

        Examples:
          | layer       | category | type     |
          | address,poi | highway  | bus_stop |
          | address     | amenity  | parking  |


     Scenario: Between natural and low-zoom address prefer natural
         When sending v1/reverse at 47.13636,9.52094
           | layer           | zoom |
           | natural,address | 15   |
         Then results contain
           | category |
           | waterway |


    Scenario Outline: Search for mountain peaks begins at level 12
        When sending v1/reverse at 47.08293,9.57109
          | layer   | zoom   |
          | natural | <zoom> |
        Then results contain
          | category   | type   |
          | <category> | <type> |

        Examples:
          | zoom | category | type  |
          | 12   | natural  | peak  |
          | 13   | waterway | river |


     Scenario Outline: Reverse search with manmade layers
        When sending v1/reverse at 32.46904,-86.44439
          | layer   |
          | <layer> |
        Then results contain
          | category   | type   |
          | <category> | <type> |

        Examples:
          | layer           | category | type        |
          | manmade         | leisure  | park        |
          | address         | highway  | residential |
          | poi             | leisure  | pitch       |
          | natural         | waterway | river       |
          | natural,manmade | leisure  | park        |

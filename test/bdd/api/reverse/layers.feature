@APIDB
Feature: Layer parameter in reverse geocoding
    Testing correct function of layer selection while reverse geocoding

    @v1-api-python-only
    Scenario: POIs are selected by default
        When sending v1/reverse at 47.14077,9.52414
        Then results contain
          | category | type      |
          | tourism  | viewpoint |


    @v1-api-python-only
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


    @v1-api-python-only
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


    @v1-api-python-only
     Scenario: Between natural and low-zoom address prefer natural
         When sending v1/reverse at 47.13636,9.52094
           | layer           | zoom |
           | natural,address | 15   |
         Then results contain
           | category |
           | waterway |


    @v1-api-python-only
    Scenario Outline: Search for mountain peaks begins at level 12
        When sending v1/reverse at 47.08221,9.56769
          | layer   | zoom   |
          | natural | <zoom> |
        Then results contain
          | category   | type   |
          | <category> | <type> |

        Examples:
          | zoom | category | type  |
          | 12   | natural  | peak  |
          | 13   | waterway | river |


    @v1-api-python-only
     Scenario Outline: Reverse serach with manmade layers
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
          | natural         | waterway | stream      |
          | natural,manmade | leisure  | park        |

Feature: Layer parameter in reverse geocoding
    Testing correct function of layer selection while reverse geocoding

    Scenario: POIs are selected by default
        When reverse geocoding 47.14077,9.52414
        Then the result contains
          | category | type      |
          | tourism  | viewpoint |

    Scenario Outline: Same address level POI with different layers
        When reverse geocoding 47.14077,9.52414
          | layer   |
          | <layer> |
        Then the result contains
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
        When reverse geocoding 47.13816,9.52168
          | layer   |
          | <layer> |
        Then the result contains
          | category   | type   |
          | <category> | <type> |

        Examples:
          | layer       | category | type     |
          | address,poi | highway  | bus_stop |
          | address     | amenity  | parking  |

     Scenario: Between natural and low-zoom address prefer natural
         When reverse geocoding 47.13636,9.52094
           | layer           | zoom |
           | natural,address | 15   |
         Then the result contains
           | category |
           | waterway |

    Scenario Outline: Search for mountain peaks begins at level 12
        When reverse geocoding 47.08293,9.57109
          | layer   | zoom   |
          | natural | <zoom> |
        Then the result contains
          | category   | type   |
          | <category> | <type> |

        Examples:
          | zoom | category | type  |
          | 12   | natural  | peak  |
          | 13   | waterway | river |

     Scenario Outline: Reverse search with manmade layers
        When reverse geocoding 32.46904,-86.44439
          | layer   |
          | <layer> |
        Then the result contains
          | category   | type   |
          | <category> | <type> |

        Examples:
          | layer           | category | type        |
          | manmade         | leisure  | park        |
          | address         | highway  | residential |
          | poi             | leisure  | pitch       |
          | natural         | waterway | river       |
          | natural,manmade | leisure  | park        |

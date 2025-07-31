Feature: Reverse geocoding
    Testing the reverse function

    Scenario: Reverse - Unknown countries fall back to default country grid
        When reverse geocoding 45.174,-103.072
        Then the result contains
          | category | type    | display_name |
          | place    | country | United States |

    Scenario: Reverse - No TIGER house number for zoom < 18
        When reverse geocoding 32.4752389363,-86.4810198619
          | zoom |
          | 17 |
        Then the result contains
          | osm_type | category |
          | way      | highway  |
        And the result contains in field address
          | road                | postcode | country_code |
          | Upper Kingston Road | 36067    | us |

    Scenario: Reverse - Address with non-numerical house number
        When reverse geocoding 47.107465,9.52838521614
        Then the result contains in field address
          | house_number | road |
          | 39A/B        | Dorfstrasse |

    Scenario: Reverse - Address with numerical house number
        When reverse geocoding 47.168440329479594,9.511551699184338
        Then the result contains in field address
          | house_number | road |
          | 6            | Schmedgässle |

    Scenario Outline: Reverse - Zoom levels below 5 result in country
        When reverse geocoding 47.16,9.51
         | zoom |
         | <zoom> |
        Then the result contains
         | display_name |
         | Liechtenstein |

        Examples:
             | zoom |
             | 0    |
             | 1    |
             | 2    |
             | 3    |
             | 4    |

    Scenario: Reverse - When on a street, the closest interpolation is shown
        When reverse geocoding 47.118457166193245,9.570678289621355
         | zoom |
         | 18 |
        Then the result contains
         | display_name |
         | 1021, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

    # github 2214
    Scenario: Reverse - Interpolations do not override house numbers when they are closer
        When reverse geocoding 47.11778,9.57255
         | zoom |
         | 18 |
        Then the result contains
         | display_name |
         | 5, Grosssteg, Steg, Triesenberg, Oberland, 9497, Liechtenstein |

    Scenario: Reverse - Interpolations do not override house numbers when they are closer (2)
        When reverse geocoding 47.11834,9.57167
         | zoom |
         | 18 |
        Then the result contains
         | display_name |
         | 3, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

    Scenario: Reverse - When on a street with zoom 18, the closest housenumber is returned
        When reverse geocoding 47.11755503977281,9.572722250405036
         | zoom |
         | 18 |
        Then the result contains in field address
         | house_number |
         | 7 |

    Scenario: Reverse - inherited address is shown by default
        When reverse geocoding 47.0629071,9.4879694
        Then the result contains
         | osm_type | category | display_name |
         | node     | office   | foo.li, 64, Hampfländer, Mäls, Balzers, Oberland, 9496, Liechtenstein |

    Scenario: Reverse - inherited address is not shown with address layer
        When reverse geocoding 47.0629071,9.4879694
         | layer |
         | address |
        Then the result contains
         | osm_type | category | display_name |
         | way      | building | 64, Hampfländer, Mäls, Balzers, Oberland, 9496, Liechtenstein |

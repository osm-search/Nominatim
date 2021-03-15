@APIDB
Feature: Reverse geocoding
    Testing the reverse function

    @Tiger
    Scenario: TIGER house number
        When sending jsonv2 reverse coordinates 32.4752389363,-86.4810198619
        Then results contain
          | osm_type | category | type |
          | way      | place    | house |
        And result addresses contain
          | house_number | road                | postcode | country_code |
          | 697          | Upper Kingston Road | 36067    | us |

    @Tiger
    Scenario: No TIGER house number for zoom < 18
        When sending jsonv2 reverse coordinates 32.4752389363,-86.4810198619
          | zoom |
          | 17 |
        Then results contain
          | osm_type | category |
          | way      | highway  |
        And result addresses contain
          | road                | postcode | country_code |
          | Upper Kingston Road | 30607    | us |

    Scenario: Interpolated house number
        When sending jsonv2 reverse coordinates 47.118533,9.57056562
        Then results contain
          | osm_type | category | type |
          | way      | place    | house |
        And result addresses contain
          | house_number | road |
          | 1019         | Grosssteg |

    Scenario: Address with non-numerical house number
        When sending jsonv2 reverse coordinates 47.107465,9.52838521614
        Then result addresses contain
          | house_number | road |
          | 39A/B        | Dorfstrasse |


    Scenario: Address with numerical house number
        When sending jsonv2 reverse coordinates 47.168440329479594,9.511551699184338
        Then result addresses contain
          | house_number | road |
          | 6            | Schmedgässle |

    Scenario Outline: Zoom levels below 5 result in country
        When sending jsonv2 reverse coordinates 47.16,9.51
         | zoom |
         | <zoom> |
        Then results contain
         | display_name |
         | Liechtenstein |

    Examples:
         | zoom |
         | 0    |
         | 1    |
         | 2    |
         | 3    |
         | 4    |

    Scenario: When on a street, the closest interpolation is shown
        When sending jsonv2 reverse coordinates 47.118457166193245,9.570678289621355
         | zoom |
         | 18 |
        Then results contain
         | display_name |
         | 1021, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

    # github 2214
    Scenario: Interpolations do not override house numbers when they are closer
        When sending jsonv2 reverse coordinates 47.11778,9.57255
         | zoom |
         | 18 |
        Then results contain
         | display_name |
         | 5, Grosssteg, Steg, Triesenberg, Oberland, 9497, Liechtenstein |

    Scenario: Interpolations do not override house numbers when they are closer (2)
        When sending jsonv2 reverse coordinates 47.11834,9.57167
         | zoom |
         | 18 |
        Then results contain
         | display_name |
         | 3, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |

    Scenario: When on a street with zoom 18, the closest housenumber is returned
        When sending jsonv2 reverse coordinates 47.11755503977281,9.572722250405036
         | zoom |
         | 18 |
        Then result addresses contain
         | house_number |
         | 7 |

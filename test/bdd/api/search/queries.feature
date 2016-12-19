@APIDB
Feature: Search queries
    Generic search result correctness

    Scenario: House number search for non-street address
        When sending json search query "2 Steinwald, Austria" with address
          | accept-language |
          | en |
        Then address of result 0 is
          | type         | value |
          | house_number | 2 |
          | hamlet       | Steinwald |
          | postcode     | 6811 |
          | country      | Austria |
          | country_code | at |

    Scenario: House number interpolation even
        When sending json search query "Schellingstr 86, Hamburg" with address
          | accept-language |
          | de |
        Then address of result 0 is
          | type         | value |
          | house_number | 86 |
          | road         | Schellingstraße |
          | suburb       | Eilbek |
          | postcode     | 22089 |
          | city_district | Wandsbek |
          | state        | Hamburg |
          | country      | Deutschland |
          | country_code | de |

    Scenario: House number interpolation odd
        When sending json search query "Schellingstr 73, Hamburg" with address
          | accept-language |
          | de |
        Then address of result 0 is
          | type         | value |
          | house_number | 73 |
          | road         | Schellingstraße |
          | suburb       | Eilbek |
          | postcode     | 22089 |
          | city_district | Wandsbek |
          | state        | Hamburg |
          | country      | Deutschland |
          | country_code | de |

    @Tiger
    Scenario: TIGER house number
        When sending json search query "323 22nd Street Southwest, Huron"
        Then results contain
         | osm_type |
         | way |

    Scenario: Search with class-type feature
        When sending jsonv2 search query "Hotel California"
        Then results contain
          | place_rank |
          | 30 |

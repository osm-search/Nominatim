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
          | type          | value |
          | house_number  | 86 |
          | road          | Schellingstraße |
          | neighbourhood | Auenviertel |
          | suburb        | Eilbek |
          | postcode      | 22089 |
          | city_district | Wandsbek |
          | country       | Deutschland |
          | country_code  | de |

    Scenario: House number interpolation odd
        When sending json search query "Schellingstr 73, Hamburg" with address
          | accept-language |
          | de |
        Then address of result 0 is
          | type          | value |
          | house_number  | 73 |
          | road          | Schellingstraße |
          | neighbourhood | Auenviertel |
          | suburb        | Eilbek |
          | postcode      | 22089 |
          | city_district | Wandsbek |
          | country       | Deutschland |
          | country_code  | de |

    Scenario: With missing housenumber search falls back to road
        When sending json search query "342 rocha, santa lucia" with address
        Then address of result 0 is
          | type         | value |
          | road         | Rocha |
          | city         | Santa Lucía |
          | state        | Canelones |
          | postcode     | 90700 |
          | country      | Uruguay |
          | country_code | uy |

    @Tiger
    Scenario: TIGER house number
        When sending json search query "323 22nd Street Southwest, Huron"
        Then results contain
         | osm_type |
         | way |

    Scenario: Search with class-type feature
        When sending jsonv2 search query "Hotel in California"
        Then results contain
          | place_rank |
          | 30 |

    Scenario: Search with specific amenity
        When sending json search query "[restaurant] Vaduz" with address
        Then result addresses contain
          | country |
          | Liechtenstein |
        And  results contain
          | class   | type |
          | amenity | restaurant |

    Scenario: Search with key-value amenity
        When sending json search query "[shop=hifi] hamburg"
        Then results contain
          | class | type |
          | shop  | hifi |

    Scenario: With multiple amenity search only the first is used
        When sending json search query "[shop=hifi] [church] hamburg"
        Then results contain
          | class | type |
          | shop  | hifi |

    Scenario: With multiple amenity search only the first is used
        When sending json search query "[church] [restaurant] hamburg"
        Then results contain
          | class   | type |
          | amenity | place_of_worship |

    Scenario: POI search near given coordinate
        When sending json search query "restaurant near 47.16712,9.51100"
        Then results contain
          | class   | type |
          | amenity | restaurant |

    Scenario: Arbitrary key/value search near given coordinate
        When sending json search query "[man_made=mast]  47.15739° N 9.61264° E"
        Then results contain
          | class    | type |
          | man_made | mast |

    Scenario: Arbitrary key/value search near given coordinate and named place
        When sending json search query "[man_made=mast] amerlugalpe  47° 9′ 26″ N 9° 36′ 45″ E"
        Then results contain
          | class    | type |
          | man_made | mast |

    Scenario: Name search near given coordinate
        When sending json search query "amerlugalpe, N 47.15739° E 9.61264°"
        Then exactly 1 result is returned

    Scenario: Name search near given coordinate without result
        When sending json search query "amerlugalpe, N 47 15 7 W 9 61 26"
        Then exactly 0 results are returned

    Scenario: Arbitrary key/value search near a road
        When sending json search query "[leisure=table_soccer_table] immenbusch"
        Then results contain
          | class   | type |
          | leisure | table_soccer_table |

    Scenario: Ignore other country codes in structured search with country
        When sending json search query ""
            | city | country |
            | li   | de      |
        Then exactly 0 results are returned

    Scenario: Ignore country searches when query is restricted to countries
        When sending json search query "de"
            | countrycodes |
            | li  |
        Then exactly 0 results are returned

    # https://trac.openstreetmap.org/ticket/5094
    Scenario: housenumbers are ordered by complete match first
        When sending json search query "6395 geminis, montevideo" with address
        Then result addresses contain
          | ID | house_number |
          | 0  | 6395 |
          | 1  | 6395 BIS |


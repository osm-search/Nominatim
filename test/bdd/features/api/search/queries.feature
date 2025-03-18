Feature: Search queries
    Generic search result correctness

    Scenario: Search for natural object
        When geocoding "Samina"
          | accept-language |
          | en |
        Then result 0 contains
          | category | type  | display_name    |
          | waterway | river | Samina, Austria |

    Scenario: House number search for non-street address
        When geocoding "6 Silum, Liechtenstein"
          | accept-language |
          | en |
        Then result 0 contains in field address
          | param        | value |
          | house_number | 6 |
          | village      | Silum |
          | town         | Triesenberg |
          | county       | Oberland |
          | postcode     | 9497 |
          | country      | Liechtenstein |
          | country_code | li |
          | ISO3166-2-lvl8  | LI-10 |

    Scenario: Search for house number interpolation
        When geocoding "Grosssteg 1023, Triesenberg"
          | accept-language |
          | de |
        Then result 0 contains in field address
          | param         | value |
          | house_number  | 1023 |
          | road          | Grosssteg |
          | village       | Sücka |
          | postcode      | 9497 |
          | town          | Triesenberg |
          | country       | Liechtenstein |
          | country_code  | li |

    Scenario: With missing housenumber search falls back to road
        When geocoding "Bündaweg 555"
        Then result 0 contains in field address
          | param         | value |
          | road          | Bündaweg |
          | village       | Silum |
          | postcode      | 9497 |
          | county        | Oberland |
          | town          | Triesenberg |
          | country       | Liechtenstein |
          | country_code  | li |
          | ISO3166-2-lvl8  | LI-10 |
        And all results have no attributes address+house_number

    Scenario Outline: Housenumber 0 can be found
        When sending v1/search with format <format>
          | q              | addressdetails |
          | Gnalpstrasse 0 | 1 |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And all results contain
          | display_name!fm | address+house_number |
          | 0,.*            | 0 |

    Examples:
        | format      | outformat |
        | xml         | xml       |
        | json        | json      |
        | jsonv2      | json      |
        | geojson     | geojson   |

    Scenario: TIGER house number
        When geocoding "697 Upper Kingston Road"
        Then all results contain
         | osm_type | display_name!fm | address+house_number |
         | way      | 697,.*          | 697 |

    Scenario: Search with class-type feature
        When geocoding "bars in ebenholz"
        Then all results contain
          | place_rank |
          | 30 |

    Scenario: Search with specific amenity
        When geocoding "[restaurant] Vaduz"
        Then all results contain
          | category | type       | address+country |
          | amenity  | restaurant | Liechtenstein |

    Scenario: Search with specific amenity also work in country
        When geocoding "restaurants in liechtenstein"
        Then all results contain
          | category | type       | address+country |
          | amenity  | restaurant | Liechtenstein |

    Scenario: Search with key-value amenity
        When geocoding "[club=scout] Vaduz"
        Then all results contain
          | category | type |
          | club     | scout |

    Scenario: POI search near given coordinate
        When geocoding "restaurant near 47.16712,9.51100"
        Then all results contain
          | category | type |
          | amenity  | restaurant |

    Scenario: Arbitrary key/value search near given coordinate
        When geocoding "[leisure=firepit]   47.150° N 9.5340493° E"
        Then all results contain
          | category | type |
          | leisure  | firepit |

    Scenario: POI search in a bounded viewbox
        When geocoding "restaurants"
          | viewbox                           | bounded |
          | 9.50830,47.15253,9.52043,47.14866 | 1 |
        Then all results contain
          | category | type       |
          | amenity  | restaurant |

    Scenario Outline: Key/value search near given coordinate can be restricted to country
        When geocoding "[natural=peak] 47.06512,9.53965"
          | countrycodes |
          | <cc> |
        Then all results contain
          | address+country_code |
          | <cc> |

        Examples:
            | cc |
            | li |
            | ch |

    Scenario: Name search near given coordinate
        When geocoding "sporry"
        Then result 0 contains
          | address+town |
          | Vaduz |
        When geocoding "sporry, 47.10791,9.52676"
        Then result 0 contains
          | address+village |
          | Triesen |

    Scenario: Name search near given coordinate without result
        When geocoding "sporry, N 47 15 7 W 9 61 26"
        Then exactly 0 results are returned

    Scenario: Arbitrary key/value search near a road
        When geocoding "[amenity=drinking_water] Wissfläckaweg"
        Then all results contain
          | category | type |
          | amenity  | drinking_water |

    Scenario: Ignore other country codes in structured search with country
        When geocoding
            | countrycodes | country |
            | li           | de      |
        Then exactly 0 results are returned

    Scenario: Ignore country searches when query is restricted to countries
        When geocoding "fr"
        Then all results contain
            | name |
            | France |
        When geocoding "fr"
            | countrycodes |
            | li  |
        Then exactly 0 results are returned

    Scenario: Country searches only return results for the given country
        When geocoding "Ans Trail"
            | countrycodes |
            | li |
        Then all results contain
            | address+country_code |
            | li |

    # https://trac.openstreetmap.org/ticket/5094
    Scenario: housenumbers are ordered by complete match first
        When geocoding "Austrasse 11, Vaduz"
        Then result 0 contains
          | address+house_number |
          | 11 |

    Scenario Outline: Coordinate searches with white spaces
        When geocoding "<data>"
        Then the result set contains exactly
          | category |
          | water    |

        Examples:
          | data |
          | sporry weiher, N 47.10791° E 9.52676° |
          | sporry weiher,	N 47.10791° E 9.52676° |
          | 	sporry weiher	, 	N 47.10791° E 9.52676° |
          | sporry weiher, N 47.10791° 		E 9.52676° |
          | sporry weiher, N 47.10791° E	9.52676° |

    Scenario: Searches with white spaces
        When geocoding "52	Bodastr,Triesenberg"
        Then all results contain
          | category | type |
          | highway  | residential |


    # github #1949
    Scenario: Addressdetails always return the place type
       When geocoding "Vaduz"
       Then result 0 contains
         | address+town |
         | Vaduz |

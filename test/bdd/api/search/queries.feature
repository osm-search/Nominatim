@APIDB
Feature: Search queries
    Generic search result correctness

    Scenario: House number search for non-street address
        When sending json search query "6 Silum, Liechtenstein" with address
          | accept-language |
          | en |
        Then address of result 0 is
          | type         | value |
          | house_number | 6 |
          | village      | Silum |
          | town         | Triesenberg |
          | county       | Oberland |
          | postcode     | 9497 |
          | country      | Liechtenstein |
          | country_code | li |
          | ISO3166-2-lvl10  | LI-10 |

    Scenario: House number interpolation
        When sending json search query "Grosssteg 1023, Triesenberg" with address
          | accept-language |
          | de |
        Then address of result 0 contains
          | type          | value |
          | house_number  | 1023 |
          | road          | Grosssteg |
          | village       | Sücka |
          | postcode      | 9497 |
          | town          | Triesenberg |
          | country       | Liechtenstein |
          | country_code  | li |

    Scenario: With missing housenumber search falls back to road
        When sending json search query "Bündaweg 555" with address
        Then address of result 0 is
          | type          | value |
          | road          | Bündaweg |
          | village       | Silum |
          | postcode      | 9497 |
          | county        | Oberland |
          | town          | Triesenberg |
          | country       | Liechtenstein |
          | country_code  | li |
          | ISO3166-2-lvl10  | LI-10 |

    Scenario Outline: Housenumber 0 can be found
        When sending <format> search query "Gnalpstrasse 0" with address
        Then results contain
          | display_name |
          | ^0,.* |
        And result addresses contain
          | house_number |
          | 0     |

    Examples:
        | format |
        | xml |
        | json |
        | jsonv2 |
        | geojson |

    @Tiger
    Scenario: TIGER house number
        When sending json search query "697 Upper Kingston Road"
        Then results contain
         | osm_type | display_name |
         | way      | ^697,.* |

    Scenario: Search with class-type feature
        When sending jsonv2 search query "bars in ebenholz"
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

    Scenario: Search with specific amenity also work in country
        When sending json search query "restaurants in liechtenstein" with address
        Then result addresses contain
          | country |
          | Liechtenstein |
        And  results contain
          | class   | type |
          | amenity | restaurant |

    Scenario: Search with key-value amenity
        When sending json search query "[club=scout] Vaduz"
        Then results contain
          | class | type |
          | club  | scout |

    Scenario: With multiple amenity search only the first is used
        When sending json search query "[club=scout] [church] vaduz"
        Then results contain
          | class | type |
          | club  | scout |
        When sending json search query "[amenity=place_of_worship] [club=scout] vaduz"
        Then results contain
          | class   | type |
          | amenity | place_of_worship |

    Scenario: POI search near given coordinate
        When sending json search query "restaurant near 47.16712,9.51100"
        Then results contain
          | class   | type |
          | amenity | restaurant |

    Scenario: Arbitrary key/value search near given coordinate
        When sending json search query "[leisure=firepit]   47.150° N 9.5340493° E"
        Then results contain
          | class   | type |
          | leisure | firepit |

    Scenario: Arbitrary key/value search near given coordinate and named place
        When sending json search query "[leisure=firepit] ebenholz  47° 9′ 26″ N 9° 36′ 45″ E"
        Then results contain
          | class    | type |
          | leisure | firepit |

    Scenario Outline: Key/value search near given coordinate can be restricted to country
        When sending json search query "[natural=peak] 47.06512,9.53965" with address
          | countrycodes |
          | <cc> |
        Then result addresses contain
          | country_code |
          | <cc> |

    Examples:
        | cc |
        | li |
        | ch |

    Scenario: Name search near given coordinate
        When sending json search query "sporry" with address
        Then result addresses contain
          | ID | town |
          | 0  | Vaduz |
        When sending json search query "sporry, 47.10791,9.52676" with address
        Then result addresses contain
          | ID | village |
          | 0  | Triesen |

    Scenario: Name search near given coordinate without result
        When sending json search query "sporry, N 47 15 7 W 9 61 26"
        Then exactly 0 results are returned

    Scenario: Arbitrary key/value search near a road
        When sending json search query "[amenity=drinking_water] Wissfläckaweg"
        Then results contain
          | class   | type |
          | amenity | drinking_water |

    Scenario: Ignore other country codes in structured search with country
        When sending json search query ""
            | city | country |
            | li   | de      |
        Then exactly 0 results are returned

    Scenario: Ignore country searches when query is restricted to countries
        When sending json search query "fr"
            | countrycodes |
            | li  |
        Then exactly 0 results are returned

    Scenario: Country searches only return results for the given country
        When sending search query "Ans Trail" with address
            | countrycodes |
            | li |
        Then result addresses contain
            | country_code |
            | li |

    # https://trac.openstreetmap.org/ticket/5094
    Scenario: housenumbers are ordered by complete match first
        When sending json search query "Austrasse 11, Vaduz" with address
        Then result addresses contain
          | ID | house_number |
          | 0  | 11 |
          | 1  | 11 a |

    Scenario Outline: Coordinate searches with white spaces
        When sending json search query "<data>"
        Then exactly 1 result is returned
        And results contain
          | class   |
          | natural |

    Examples:
      | data |
      | sporry weiher, N 47.10791° E 9.52676° |
      | sporry weiher,	N 47.10791° E 9.52676° |
      | 	sporry weiher	, 	N 47.10791° E 9.52676° |
      | sporry weiher, N 47.10791° 		E 9.52676° |
      | sporry weiher, N 47.10791° E	9.52676° |

    Scenario: Searches with white spaces
        When sending json search query "52	Bodastr,Triesenberg"
        Then results contain
          | class   | type |
          | highway | residential |


    # github #1949
    Scenario: Addressdetails always return the place type
       When sending json search query "Vaduz" with address
       Then result addresses contain
         | ID | town |
         | 0  | Vaduz |

    Scenario: Search can handle complex query word sets
       When sending search query "aussenstelle universitat lichtenstein wachterhaus aussenstelle universitat lichtenstein wachterhaus aussenstelle universitat lichtenstein wachterhaus aussenstelle universitat lichtenstein wachterhaus"
       Then a HTTP 200 is returned

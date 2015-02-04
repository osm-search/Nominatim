Feature: API regression tests
    Tests error cases reported in tickets.

    Scenario: trac #2430
        When sending json search query "89 River Avenue, Hoddesdon, Hertfordshire, EN11 0JT"
        Then at least 1 result is returned

    Scenario: trac #2440
        When sending json search query "East Harvard Avenue, Denver"
        Then more than 2 results are returned

    Scenario: trac #2456
        When sending xml search query "Borlänge Kommun"
        Then results contain
         | ID | place_rank
         | 0  | 19

    Scenario: trac #2530
        When sending json search query "Lange Straße, Bamberg" with address
        Then result addresses contain
         | ID | town
         | 0  | Bamberg

    Scenario: trac #2541
        When sending json search query "pad, germany"
        Then results contain
         | ID | class   | display_name
         | 0  | aeroway | Paderborn/Lippstadt,.*

    Scenario: trac #2579
        When sending json search query "Johnsons Close, hackbridge" with address
        Then result addresses contain
         | ID | postcode
         | 0  | SM5 2LU

    @Fail
    Scenario Outline: trac #2586
        When sending json search query "<query>" with address
        Then result addresses contain
         | ID | country_code
         | 0  | uk

    Examples:
        | query
        | DL7 0SN
        | DL70SN

    Scenario: trac #2628 (1)
        When sending json search query "Adam Kraft Str" with address
        Then result addresses contain
         | ID | road          
         | 0  | Adam-Kraft-Straße

    Scenario: trac #2628 (2)
        When sending json search query "Maxfeldstr. 5, Nürnberg" with address
        Then result addresses contain
         | ID | house_number | road          | city
         | 0  | 5            | Maxfeldstraße | Nürnberg

    Scenario: trac #2638
        When sending json search query "Nöthnitzer Str. 40, 01187 Dresden" with address
        Then result addresses contain
         | ID | house_number | road              | city
         | 0  | 40           | Nöthnitzer Straße | Dresden

    Scenario Outline: trac #2667
        When sending json search query "<query>" with address
        Then result addresses contain
         | ID | house_number
         | 0  | <number>

    Examples:
        | number | query
        | 16     | 16 Woodpecker Way, Cambourne
        | 14906  | 14906, 114 Street Northwest, Edmonton, Alberta, Canada
        | 14904  | 14904, 114 Street Northwest, Edmonton, Alberta, Canada
        | 15022  | 15022, 114 Street Northwest, Edmonton, Alberta, Canada
        | 15024  | 15024, 114 Street Northwest, Edmonton, Alberta, Canada

    Scenario: trac #2681
        When sending json search query "kirchstraße troisdorf Germany"
        Then results contain
         | ID | display_name
         | 0  | .*, Troisdorf, .*

    Scenario: trac #2758
        When sending json search query "6а, полуботка, чернигов" with address
        Then result addresses contain
         | ID | house_number
         | 0  | 6а

    Scenario: trac #2790
        When looking up coordinates 49.0942079697809,8.27565898861822
        Then result addresses contain
         | ID | road          | village  | country
         | 0  | Daimlerstraße | Jockgrim | Deutschland

    Scenario: trac #2794
        When sending json search query "4008"
        Then results contain
         | ID | class | type
         | 0  | place | postcode

    Scenario: trac #2797
        When sending json search query "Philippstr.4, 52349 Düren" with address
        Then result addresses contain
         | ID | road          | town
         | 0  | Philippstraße | Düren

    Scenario: trac #2830
        When sending json search query "528, Merkley Drive, K4A 1N5,CA" with address
        Then result addresses contain
         | ID | house_number | road          | postcode | country
         | 0  | 528          | Merkley Drive | K4A 1N5  | Canada

    Scenario: trac #2830
        When sending json search query "K4A 1N5,CA"
        Then results contain
         | ID | class | type     | display_name
         | 0  | place | postcode | .*, Canada

    Scenario: trac #2845
        When sending json search query "Leliestraat 31, Zwolle" with address
        Then result addresses contain
         | ID | city
         | 0  | Zwolle

    Scenario: trac #2852
        When sending json search query "berlinerstrasse, leipzig" with address
        Then result addresses contain
         | ID | road
         | 0  | Berliner Straße

    Scenario: trac #2871
        When looking up coordinates -33.906895553,150.99609375
        Then result addresses contain
         | ID | city       | postcode | country
         | 0  | [^0-9]*    | 2197     | Australia

    Scenario: trac #2974
        When sending json search query "Azadi Square, Faruj" with address
        Then result addresses contain
         | ID | road        | city
         | 0  | ميدان آزادي | فاروج
        And results contain
         | ID | latlon
         | 0  | 37.2323,58.2193 +-1km

     Scenario: trac #2981
        When sending json search query "Ohmstraße 7, Berlin" with address
        Then at least 2 results are returned
        And result addresses contain
         | house_number | road      | state
         | 7            | Ohmstraße | Berlin

     Scenario: trac #3049
        When sending json search query "Soccer City"
        Then results contain
         | ID | class   | type    | latlon
         | 0  | leisure | stadium | -26.2347261,27.982645 +-50m

     Scenario: trac #3130
        When sending json search query "Old Way, Frinton"
        Then results contain
         | ID | class   | latlon
         | 0  | highway | 51.8324206,1.2447352 +-100m

     Scenario: trac #5238
        Given the request parameters
         | bounded | viewbox
         | 1       | 0,0,-1,-1
        When sending json search query "sy"
        Then exactly 0 results are returned

    Scenario: trac #5274
        When sending json search query "Goedestraat 41-BS, Utrecht" with address
        Then result addresses contain
          | house_number | road        | city
          | 41-BS        | Goedestraat | Utrecht

    @poldi-only
    Scenario Outline: github #36
        When sending json search query "<query>" with address
        Then result addresses contain
         | ID | road     | city
         | 0  | Seegasse | Wieselburg-Land

    Examples:
         | query
         | Seegasse, Gemeinde Wieselburg-Land
         | Seegasse, Wieselburg-Land
         | Seegasse, Wieselburg

    Scenario: github #190
        When looking up place N257363453
        Then the results contain
         | osm_type   | osm_id     | latlon
         | node       | 257363453  | 35.8404121,128.5586643 +-100m


Feature: Tiger geocoding
    Testing the forward and reverse Geocoding functions with tiger lines


    @Tiger
    Scenario: TIGER house number in Bismarck ND
        Given the request parameters
          | addressdetails
          | 1
        When looking up coordinates 46.806715,-100.765655
        And exactly 1 result is returned
        And result addresses contain
          | ID | house_number | road               | postcode | country_code
          | 0  | 1746         | East Broadway Avenue     | 58501    | us
        And result 0 has not attributes osm_id,osm_type

    @Tiger
        Scenario: No TIGER house number for zoom < 18
            Given the request parameters
              | addressdetails | zoom
              | 1              | 17
            When looking up coordinates 46.806715,-100.765655
            And exactly 1 result is returned
            And result addresses contain
              | ID | road               | postcode | country_code
              | 0  | East Broadway Avenue   | 58501    | us
            And result 0 has attributes osm_id,osm_type

    @Tiger
    Scenario: TIGER house number
        When sending json search query "2501 Harding Avenue, Bismarck"
        Then result 0 has not attributes osm_id,osm_type

    @Tiger
    Scenario: TIGER house number (road fallback)
        When sending json search query "1 Harding Avenue, Bismarck"
        Then result 0 has attributes osm_id,osm_type
    
    @Tiger
    Scenario: TIGER accepted-language
        Given the request parameters
          | addressdetails | accept-language
          | 1              | de
        When looking up coordinates 46.806715,-100.765655
        And exactly 1 result is returned
        And result addresses contain
          | ID | house_number | road                  | postcode | country                        |country_code
          | 0  | 1746         | East Broadway Avenue  | 58501    | Vereinigte Staaten von Amerika | us
        And result 0 has not attributes osm_id,osm_type
        

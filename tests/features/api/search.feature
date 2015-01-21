Feature: Search queries
    Testing correctness of results

    Scenario: UK House number search
        When sending json search query "27 Thoresby Road, Broxtowe" with address
        Then address of result 0 contains
          | type         | value
          | house_number | 27
          | road         | Thoresby Road
          | city         | Broxtowe
          | state        | England
          | country      | United Kingdom
          | country_code | gb


    Scenario: House number search for non-street address
        Given the request parameters
          | accept-language
          | en
        When sending json search query "4 Pomocnia, Pokrzywnica, Poland" with address
        Then address of result 0 is
          | type         | value
          | house_number | 4
          | city         | Pomocnia
          | county       | gmina Pokrzywnica
          | state        | Masovian Voivodeship
          | postcode     | 06-121
          | country      | Poland
          | country_code | pl

    Scenario: House number interpolation even
        Given the request parameters
          | accept-language
          | en        
        When sending json search query "140 rue Don Bosco, Saguenay" with address
        Then address of result 0 contains
          | type         | value
          | house_number | 140
          | road         | rue Don Bosco
          | city         | Saguenay
          | state        | Quebec
          | country      | Canada
          | country_code | ca

    Scenario: House number interpolation odd
        Given the request parameters
          | accept-language
          | en        
        When sending json search query "141 rue Don Bosco, Saguenay" with address
        Then address of result 0 contains
          | type         | value
          | house_number | 141
          | road         | rue Don Bosco
          | city         | Saguenay
          | state        | Quebec
          | country      | Canada
          | country_code | ca

    Scenario: TIGER house number
        When sending json search query "3 West Victory Way, Craig"
        Then result 0 has not attributes osm_id,osm_type

    Scenario: TIGER house number (road fallback)
        When sending json search query "3030 West Victory Way, Craig"
        Then result 0 has attributes osm_id,osm_type

    Scenario: Expansion of Illinois
        Given the request parameters
          | accept-language
          | en        
        When sending json search query "il, us"
        Then results contain
          | ID | display_name
          | 0  | Illinois.*

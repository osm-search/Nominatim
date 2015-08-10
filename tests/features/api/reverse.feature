Feature: Reverse geocoding
    Testing the reverse function

    # Make sure country is not overwritten by the postcode
    Scenario: Country is returned
        Given the request parameters
          | accept-language
          | de
        When looking up coordinates 53.9788769,13.0830313
        Then result addresses contain 
         | ID | country
         | 0  | Deutschland

    @Tiger
    Scenario: TIGER house number
        Given the request parameters
          | addressdetails
          | 1
        When looking up coordinates 40.6863624710666,-112.060005720023
        And exactly 1 result is returned
        And result addresses contain
          | ID | house_number | road               | postcode | country_code
          | 0  | 7094         | Kings Estate Drive | 84128    | us
        And result 0 has not attributes osm_id,osm_type


    @Tiger
    Scenario: No TIGER house number for zoom < 18
        Given the request parameters
          | addressdetails | zoom
          | 1              | 17
        When looking up coordinates 40.6863624710666,-112.060005720023
        And exactly 1 result is returned
        And result addresses contain
          | ID | road               | postcode | country_code
          | 0  | Kings Estate Drive | 84128    | us
        And result 0 has attributes osm_id,osm_type

   Scenario Outline: Reverse Geocoding with extratags
        Given the request parameters
          | extratags
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes extratags

   Examples:
        | format
        | xml
        | json
        | jsonv2

   Scenario Outline: Reverse Geocoding with namedetails
        Given the request parameters
          | namedetails
          | 1
        When looking up <format> coordinates 48.86093,2.2978
        Then result 0 has attributes namedetails

   Examples:
        | format
        | xml
        | json
        | jsonv2

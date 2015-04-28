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
        When looking up jsonv2 coordinates 40.6863624710666,-112.060005720023
        # Then exactly 1 result is returned
        # Then result addresses contain
        # | ID | house_number | road               | postcode | country_code
        # | 0  | 7094         | Kings Estate Drive | 84128    | us
        Then results contain
          | type | house
        And results contain
          | addresstype | place
        And results contain
          | road | Kings Estate Drive
        And results contain
          | house_number | 7094
        And results contain
          | postcode | 84128

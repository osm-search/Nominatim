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


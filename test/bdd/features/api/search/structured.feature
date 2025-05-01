Feature: Structured search queries
    Testing correctness of results with
    structured queries

    Scenario: Structured search for country only
        When geocoding
          | country |
          | Liechtenstein |
        Then all results contain in field address
          | country_code | country       |
          | li           | Liechtenstein |

    Scenario: Structured search for postcode only
        When geocoding
          | postalcode |
          | 9495 |
        Then all results contain
          | type!fm         | address+postcode |
          | ^post(al_)?code | 9495             |

    Scenario: Structured search for street, postcode and country
        When sending v1/search with format xml
          | street          | postalcode | country        |
          | Old Palace Road | GU2 7UP    | United Kingdom |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result metadata contains
          | querystring |
          | Old Palace Road, GU2 7UP, United Kingdom |

    Scenario: Structured search for street with housenumber, city and postcode
        When geocoding
          | street             | city  | postalcode |
          | 19 Am schrägen Weg | Vaduz | 9490       |
        Then all results contain in field address
          | house_number | road |
          | 19           | Am Schrägen Weg |

    Scenario: Structured search for street with housenumber, city and bad postcode
        When geocoding
          | street             | city  | postalcode |
          | 19 Am schrägen Weg | Vaduz | 9491       |
        Then all results contain in field address
          | house_number | road |
          | 19           | Am Schrägen Weg |

    Scenario: Structured search for amenity, city
        When geocoding
          | city  | amenity |
          | Vaduz | bar  |
        Then all results contain
          | address+country | category | type!fm |
          | Liechtenstein   | amenity  | (pub)\|(bar)\|(restaurant) |

    #176
    Scenario: Structured search restricts rank
        When geocoding
          | city |
          | Steg |
        Then all results contain
          | addresstype |
          | village |

    #3651
    Scenario: Structured search with surrounding extra characters
        When geocoding
          | street               | city  | postalcode |
          | "19 Am schrägen Weg" | "Vaduz" | "9491"  |
        Then all results contain in field address
          | house_number | road |
          | 19           | Am Schrägen Weg |


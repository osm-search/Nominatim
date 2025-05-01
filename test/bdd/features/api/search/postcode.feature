Feature: Searches with postcodes
    Various searches involving postcodes

    Scenario: US 5+4 ZIP codes are shortened to 5 ZIP codes if not found
        When geocoding "36067-1111, us"
        Then all results contain in field address
            | postcode |
            | 36067    |
        And all results contain
            | type     |
            | postcode |

    Scenario: Postcode search with address
        When geocoding "9486, mauren"
        Then result 0 contains
            | type     |
            | postcode |

    Scenario: Postcode search with country
        When geocoding "9486, li"
        Then all results contain in field address
            | country_code |
            | li           |

    Scenario: Postcode search with country code restriction
        When geocoding "9490"
            | countrycodes |
            | li |
        Then all results contain in field address
            | country_code |
            | li           |

    Scenario: Postcode search with bounded viewbox restriction
        When geocoding "9486"
          | bounded | viewbox |
          | 1       | 9.55,47.20,9.58,47.22 |
        Then all results contain in field address
            | postcode |
            | 9486     |
        When geocoding "9486"
          | bounded | viewbox                 |
          | 1       | 5.00,20.00,6.00,21.00 |
        Then exactly 0 result is returned

    Scenario: Postcode search with structured query
        When geocoding ""
            | postalcode | country |
            | 9490       | li |
        Then all results contain in field address
            | country_code | postcode |
            | li           | 9490     |

@APIDB
Feature: Searches with postcodes
    Various searches involving postcodes

    Scenario: US 5+4 ZIP codes are shortened to 5 ZIP codes if not found
        When sending json search query "57701 1111, us" with address
        Then result addresses contain
            | postcode |
            | 57701    |

    Scenario: Postcode search with address
        When sending json search query "9486, mauren"
        Then at least 1 result is returned

    Scenario: Postcode search with country
        When sending json search query "9486, li" with address
        Then result addresses contain
            | country_code |
            | li           |

    Scenario: Postcode search with country code restriction
        When sending json search query "9490" with address
            | countrycodes |
            | li |
        Then result addresses contain
            | country_code |
            | li           |

    Scenario: Postcode search with bounded viewbox restriction
        When sending json search query "9486" with address
          | bounded | viewbox |
          | 1       | 9.55,47.20,9.58,47.22 |
        Then result addresses contain
            | postcode |
            | 9486     |
        When sending json search query "9486" with address
          | bounded | viewbox                 |
          | 1       | 5.00,20.00,6.00,21.00 |
        Then exactly 0 results are returned

    Scenario: Postcode search with structured query
        When sending json search query "" with address
            | postalcode | country |
            | 9490       | li |
        Then result addresses contain
            | country_code | postcode |
            | li           | 9490     |

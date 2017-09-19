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


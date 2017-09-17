@APIDB
Feature: Structured search queries
    Testing correctness of results with
    structured queries

    Scenario: Country only
        When sending json search query "" with address
          | country |
          | Liechtenstein |
        Then address of result 0 is
          | type         | value |
          | country      | Liechtenstein |
          | country_code | li |

    Scenario: Postcode only
        When sending json search query "" with address
          | postalcode |
          | 22547 |
        Then results contain
          | type |
          | postcode |
        And result addresses contain
          | postcode |
          | 22547 |

    Scenario: Street, postcode and country
        When sending xml search query "" with address
          | street          | postalcode | country |
          | Old Palace Road | GU2 7UP    | United Kingdom |
        Then result header contains
          | attr        | value |
          | querystring | Old Palace Road, GU2 7UP, United Kingdom |

    Scenario: Amenity, city
        When sending json search query "" with address
          | city  | amenity |
          | Vaduz | church  |
        Then result addresses contain
          | country |
          | Liechtenstein |
        And  results contain
          | class   | type |
          | amenity | place_of_worship |

    Scenario: gihub #176
        When sending json search query "" with address
          | city |
          | Mercedes |
        Then at least 1 result is returned

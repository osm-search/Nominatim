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
          | 9495 |
        Then results contain
          | type |
          | ^post(al_)?code |
        And result addresses contain
          | postcode |
          | 9495 |

    Scenario: Street, postcode and country
        When sending xml search query "" with address
          | street          | postalcode | country |
          | Old Palace Road | GU2 7UP    | United Kingdom |
        Then result header contains
          | attr        | value |
          | querystring | Old Palace Road, GU2 7UP, United Kingdom |

    Scenario: Street with housenumber, city and postcode
        When sending xml search query "" with address
          | street             | city  | postalcode |
          | 19 Am schrägen Weg | Vaduz | 9490       |
        Then result addresses contain
          | house_number | road |
          | 19           | Am Schrägen Weg |

    Scenario: Street with housenumber, city and bad postcode
        When sending xml search query "" with address
          | street             | city  | postalcode |
          | 19 Am schrägen Weg | Vaduz | 9491       |
        Then result addresses contain
          | house_number | road |
          | 19           | Am Schrägen Weg |

    Scenario: Amenity, city
        When sending json search query "" with address
          | city  | amenity |
          | Vaduz | bar  |
        Then result addresses contain
          | country |
          | Liechtenstein |
        And  results contain
          | class   | type |
          | amenity | ^(pub)\|(bar) |

    #176
    Scenario: Structured search restricts rank
        When sending json search query "" with address
          | city |
          | Vaduz |
        Then result addresses contain
          | town |
          | Vaduz |

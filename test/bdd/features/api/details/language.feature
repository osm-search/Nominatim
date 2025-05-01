Feature: Localization of search results

    Scenario: default language
        When sending v1/details
          | osmtype | osmid   |
          | R       | 1155955 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | localname |
          | Liechtenstein |

    Scenario: accept-language first
        When sending v1/details
          | osmtype | osmid   | accept-language |
          | R       | 1155955 | zh,de |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | localname |
          | 列支敦士登 |

    Scenario: accept-language missing
        When sending v1/details
          | osmtype | osmid   | accept-language |
          | R       | 1155955 | xx,fr,en,de |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | localname |
          | Liechtenstein |

    Scenario: http accept language header first
        Given the HTTP header
          | accept-language |
          | fo;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending v1/details
          | osmtype | osmid   |
          | R       | 1155955 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | localname |
          | Liktinstein |

    Scenario: http accept language header and accept-language
        Given the HTTP header
          | accept-language |
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending v1/details
          | osmtype | osmid   | accept-language |
          | R       | 1155955 | fo,en |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | localname |
          | Liktinstein |

    Scenario: http accept language header fallback
        Given the HTTP header
          | accept-language |
          | fo-ca,en-ca;q=0.5 |
        When sending v1/details
          | osmtype | osmid   |
          | R       | 1155955 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | localname |
          | Liktinstein |

    Scenario: http accept language header fallback (upper case)
        Given the HTTP header
          | accept-language |
          | fo-FR;q=0.8,en-ca;q=0.5 |
        When sending v1/details
          | osmtype | osmid   |
          | R       | 1155955 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | localname |
          | Liktinstein |

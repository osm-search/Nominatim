Feature: Localization of search results

    Scenario: Search - default language
        When sending v1/search
          | q |
          | Liechtenstein |
        Then a HTTP 200 is returned
        And the result is valid json
        And result 0 contains
          | display_name |
          | Liechtenstein |

    Scenario: Search - accept-language first
        When sending v1/search
          | q             | accept-language |
          | Liechtenstein | zh,de |
        Then a HTTP 200 is returned
        And the result is valid json
        And result 0 contains
          | display_name |
          | 列支敦士登 |

    Scenario: Search - accept-language missing
        When sending v1/search
          | q             | accept-language |
          | Liechtenstein | xx,fr,en,de |
        Then a HTTP 200 is returned
        And the result is valid json
        And result 0 contains
          | display_name |
          | Liechtenstein |

    Scenario: Search - http accept language header first
        Given the HTTP header
          | accept-language |
          | fo;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending v1/search
          | q |
          | Liechtenstein |
        Then a HTTP 200 is returned
        And the result is valid json
        And result 0 contains
          | display_name |
          | Liktinstein |

    Scenario: Search - http accept language header and accept-language
        Given the HTTP header
          | accept-language |
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending v1/search
          | q | accept-language |
          | Liechtenstein | fo,en |
        Then a HTTP 200 is returned
        And the result is valid json
        And result 0 contains
          | display_name |
          | Liktinstein |

    Scenario: Search - http accept language header fallback
        Given the HTTP header
          | accept-language |
          | fo-ca,en-ca;q=0.5 |
        When sending v1/search
          | q |
          | Liechtenstein |
        Then a HTTP 200 is returned
        And the result is valid json
        And result 0 contains
          | display_name |
          | Liktinstein |

    Scenario: Search - http accept language header fallback (upper case)
        Given the HTTP header
          | accept-language |
          | fo-FR;q=0.8,en-ca;q=0.5 |
        When sending v1/search
          | q |
          | Liechtenstein |
        Then a HTTP 200 is returned
        And the result is valid json
        And result 0 contains
          | display_name |
          | Liktinstein |

Feature: Localization of reverse search results

    Scenario: Reverse - default language
        When sending v1/reverse with format jsonv2
          | lat   | lon  |
          | 47.14 | 9.55 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | address+country |
          | Liechtenstein |

    Scenario: Reverse - accept-language parameter
        When sending v1/reverse with format jsonv2
          | lat   | lon  | accept-language |
          | 47.14 | 9.55 | ja,en |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | address+country |
          | リヒテンシュタイン |

    Scenario: Reverse - HTTP accept language header
        Given the HTTP header
          | accept-language |
          | fo-ca,fo;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending v1/reverse with format jsonv2
          | lat   | lon  |
          | 47.14 | 9.55 |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | address+country |
          | Liktinstein |

    Scenario: Reverse - accept-language parameter and HTTP header
        Given the HTTP header
          | accept-language |
          | fo-ca,fo;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending v1/reverse with format jsonv2
          | lat   | lon  | accept-language |
          | 47.14 | 9.55 | en |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | address+country |
          | Liechtenstein |

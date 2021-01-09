@APIDB
Feature: Localization of reverse search results

    Scenario: default language
        When sending json reverse coordinates 47.14,9.55
        Then result addresses contain
          | ID | country |
          | 0  | Liechtenstein |

    Scenario: accept-language parameter
        When sending json reverse coordinates 47.14,9.55
          | accept-language |
          | ja,en |
        Then result addresses contain
          | ID | country |
          | 0  | リヒテンシュタイン |

    Scenario: HTTP accept language header
        Given the HTTP header
          | accept-language |
          | fo-ca,fo;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending json reverse coordinates 47.14,9.55
        Then result addresses contain
          | ID | country |
          | 0  | Liktinstein |

    Scenario: accept-language parameter and HTTP header
        Given the HTTP header
          | accept-language |
          | fo-ca,fo;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending json reverse coordinates 47.14,9.55
          | accept-language |
          | en |
        Then result addresses contain
          | ID | country |
          | 0  | Liechtenstein |

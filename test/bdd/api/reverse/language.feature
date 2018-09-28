@APIDB
Feature: Localization of reverse search results

    Scenario: default language
        When sending json reverse coordinates 18.1147,-15.95
        Then result addresses contain
          | ID | country |
          | 0  | موريتانيا |

    Scenario: accept-language parameter
        When sending json reverse coordinates 18.1147,-15.95
          | accept-language |
          | en,fr |
        Then result addresses contain
          | ID | country |
          | 0  | Mauritania |

    Scenario: HTTP accept language header
        Given the HTTP header
          | accept-language |
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending json reverse coordinates 18.1147,-15.95
        Then result addresses contain
          | ID | country |
          | 0  | Mauritanie |

    Scenario: accept-language parameter and HTTP header
        Given the HTTP header
          | accept-language |
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending json reverse coordinates 18.1147,-15.95
          | accept-language |
          | en |
        Then result addresses contain
          | ID | country |
          | 0  | Mauritania |

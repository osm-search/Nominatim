@APIDB
Feature: Localization of search results

    Scenario: default language
        When sending json search query "Vietnam"
        Then results contain
          | ID | display_name |
          | 0  | Việt Nam |

    Scenario: accept-language first
        When sending json search query "Mauretanien"
          | accept-language |
          | en,de |
        Then results contain
          | ID | display_name |
          | 0  | Mauritania |

    Scenario: accept-language missing
        When sending json search query "Mauretanien"
          | accept-language |
          | xx,fr,en,de |
        Then results contain
          | ID | display_name |
          | 0  | Mauritanie |

    Scenario: http accept language header first
        Given the HTTP header
          | accept-language |
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending json search query "Mauretanien"
        Then results contain
          | ID | display_name |
          | 0  | Mauritanie |

    Scenario: http accept language header and accept-language
        Given the HTTP header
          | accept-language |
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending json search query "Mauretanien"
          | accept-language |
          | de,en |
        Then results contain
          | ID | display_name |
          | 0  | Mauretanien |

    Scenario: http accept language header fallback
        Given the HTTP header
          | accept-language |
          | fr-ca,en-ca;q=0.5 |
        When sending json search query "Mauretanien"
        Then results contain
          | ID | display_name |
          | 0  | Mauritanie |

    Scenario: http accept language header fallback (upper case)
        Given the HTTP header
          | accept-language |
          | fr-FR;q=0.8,en-ca;q=0.5 |
        When sending json search query "Mauretanien"
        Then results contain
          | ID | display_name |
          | 0  | Mauritanie |

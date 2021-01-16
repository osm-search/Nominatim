@APIDB
Feature: Localization of search results

    Scenario: default language
        When sending details query for R1155955
        Then results contain
          | ID | localname |
          | 0  | Liechtenstein |

    Scenario: accept-language first
        When sending details query for R1155955
          | accept-language |
          | zh,de |
        Then results contain
          | ID | localname |
          | 0  | 列支敦士登 |

    Scenario: accept-language missing
        When sending details query for R1155955
          | accept-language |
          | xx,fr,en,de |
        Then results contain
          | ID | localname |
          | 0  | Liechtenstein |

    Scenario: http accept language header first
        Given the HTTP header
          | accept-language |
          | fo;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending details query for R1155955
        Then results contain
          | ID | localname |
          | 0  | Liktinstein |

    Scenario: http accept language header and accept-language
        Given the HTTP header
          | accept-language |
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3 |
        When sending details query for R1155955
          | accept-language |
          | fo,en |
        Then results contain
          | ID | localname |
          | 0  | Liktinstein |

    Scenario: http accept language header fallback
        Given the HTTP header
          | accept-language |
          | fo-ca,en-ca;q=0.5 |
        When sending details query for R1155955
        Then results contain
          | ID | localname |
          | 0  | Liktinstein |

    Scenario: http accept language header fallback (upper case)
        Given the HTTP header
          | accept-language |
          | fo-FR;q=0.8,en-ca;q=0.5 |
        When sending details query for R1155955
        Then results contain
          | ID | localname |
          | 0  | Liktinstein |

Feature: Localization of search results

    Scenario: Search - default language
        When sending json search query "Germany"
        Then results contain
          | ID | display_name
          | 0  | Deutschland.*

    Scenario: Search - accept-language first
        Given the request parameters
          | accept-language
          | en,de
        When sending json search query "Deutschland"
        Then results contain
          | ID | display_name
          | 0  | Germany.*
        
    Scenario: Search - accept-language missing
        Given the request parameters
          | accept-language
          | xx,fr,en,de
        When sending json search query "Deutschland"
        Then results contain
          | ID | display_name
          | 0  | Allemagne.*

    Scenario: Search - http accept language header first
        Given the HTTP header
          | accept-language
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3
        When sending json search query "Deutschland"
        Then results contain
          | ID | display_name
          | 0  | Allemagne.*

    Scenario: Search - http accept language header and accept-language
        Given the request parameters
          | accept-language
          | de,en
        Given the HTTP header
          | accept-language
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3
        When sending json search query "Deutschland"
        Then results contain
          | ID | display_name
          | 0  | Deutschland.*

    Scenario: Search - http accept language header fallback
        Given the HTTP header
          | accept-language
          | fr-ca,en-ca;q=0.5
        When sending json search query "Deutschland"
        Then results contain
          | ID | display_name
          | 0  | Allemagne.*

    Scenario: Search - http accept language header fallback (upper case)
        Given the HTTP header
          | accept-language
          | fr-FR;q=0.8,en-ca;q=0.5
        When sending json search query "Deutschland"
        Then results contain
          | ID | display_name
          | 0  | Allemagne.*

    Scenario: Reverse - default language
        When looking up coordinates 48.13921,11.57328
        Then result addresses contain
          | ID | city
          | 0  | München

    Scenario: Reverse - accept-language parameter
        Given the request parameters
          | accept-language
          | en,fr
        When looking up coordinates 48.13921,11.57328
        Then result addresses contain
          | ID | city
          | 0  | Munich

    Scenario: Reverse - HTTP accept language header
        Given the HTTP header
          | accept-language
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3
        When looking up coordinates 48.13921,11.57328
        Then result addresses contain
          | ID | city
          | 0  | Munich
    
    Scenario: Reverse - accept-language parameter and HTTP header
        Given the request parameters
          | accept-language
          | it
        Given the HTTP header
          | accept-language
          | fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3
        When looking up coordinates 48.13921,11.57328
        Then result addresses contain
          | ID | city
          | 0  | Monaco di Baviera

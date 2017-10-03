@APIDB
Feature: Reverse geocoding
    Testing the reverse function

    @Tiger
    Scenario: TIGER house number
        When sending jsonv2 reverse coordinates 45.3345,-97.5214
        Then results contain
          | osm_type | category | type |
          | way      | place    | house |
        And result addresses contain
          | house_number | road            | postcode | country_code |
          | 906          | West 1st Street | 57274    | us |

    @Tiger
    Scenario: No TIGER house number for zoom < 18
        When sending jsonv2 reverse coordinates 45.3345,-97.5214
          | zoom |
          | 17 |
        Then results contain
          | osm_type | category |
          | way      | highway  |
        And result addresses contain
          | road            | postcode | country_code |
          | West 1st Street | 57274    | us |

    Scenario: Interpolated house number
        When sending jsonv2 reverse coordinates -33.231795578514635,-54.38682173844428
        Then results contain
          | osm_type | category | type |
          | way      | place    | house |
        And result addresses contain
          | house_number | road |
          | 1410         | Juan Antonio Lavalleja |

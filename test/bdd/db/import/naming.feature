@DB
Feature: Import and search of names
    Tests all naming related import issues

    Scenario: No copying name tag if only one name
        Given the places
          | osm | class | type      | name   | geometry |
          | N1  | place | locality  | german | country:de |
        When importing
        Then placex contains
          | object | calculated_country_code | name+name |
          | N1     | de                      | german |

    Scenario: Copying name tag to default language if it does not exist
        Given the places
          | osm | class | type      | name   | name+name:fi | geometry |
          | N1  | place | locality  | german | finnish      | country:de |
        When importing
        Then placex contains
          | object | calculated_country_code | name   | name+name:fi | name+name:de |
          | N1     | de                      | german | finnish      | german       |

    Scenario: Copying default language name tag to name if it does not exist
        Given the places
          | osm | class | type     | name+name:de | name+name:fi | geometry |
          | N1  | place | locality | german       | finnish      | country:de |
        When importing
        Then placex contains
          | object | calculated_country_code | name   | name+name:fi | name+name:de |
          | N1     | de                      | german | finnish      | german       |

    Scenario: Do not overwrite default language with name tag
        Given the places
          | osm | class | type     | name   | name+name:fi | name+name:de | geometry |
          | N1  | place | locality | german | finnish      | local        | country:de |
        When importing
        Then placex contains
          | object | calculated_country_code | name   | name+name:fi | name+name:de |
          | N1     | de                      | german | finnish      | local        |

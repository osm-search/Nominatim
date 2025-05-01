Feature: Import and search of names
    Tests all naming related import issues

    Scenario: No copying name tag if only one name
        Given the places
          | osm | class | type      | name+name | geometry |
          | N1  | place | locality  | german    | country:de |
        When importing
        Then placex contains
          | object | country_code | name+name |
          | N1     | de           | german |

    Scenario: Copying name tag to default language if it does not exist
        Given the places
          | osm | class | type      | name+name | name+name:fi | geometry |
          | N1  | place | locality  | german    | finnish      | country:de |
        When importing
        Then placex contains
          | object | country_code | name+name | name+name:fi | name+name:de |
          | N1     | de           | german    | finnish      | german       |

    Scenario: Copying default language name tag to name if it does not exist
        Given the places
          | osm | class | type     | name+name:de | name+name:fi | geometry |
          | N1  | place | locality | german       | finnish      | country:de |
        When importing
        Then placex contains
          | object | country_code | name+name | name+name:fi | name+name:de |
          | N1     | de           | german    | finnish      | german       |

    Scenario: Do not overwrite default language with name tag
        Given the places
          | osm | class | type     | name+name | name+name:fi | name+name:de | geometry |
          | N1  | place | locality | german    | finnish      | local        | country:de |
        When importing
        Then placex contains
          | object | country_code | name+name | name+name:fi | name+name:de |
          | N1     | de           | german    | finnish      | local        |

    Scenario Outline: Names in any script can be found
        Given the places
            | osm | class | type   | name+name   |
            | N1  | place | hamlet | <name> |
        When importing
        And geocoding "<name>"
        Then the result set contains
            | object |
            | N1  |

     Examples:
        | name |
        | Berlin |
        | 北京 |
        | Вологда |
        | Αθήνα |
        | القاهرة |
        | រាជធានីភ្នំពេញ |
        | 東京都 |
        | ပုဗ္ဗသီရိ |


    Scenario: German umlauts can be found when expanded
        Given the places
            | osm | class | type | name+name:de |
            | N1  | place | city | Münster      |
            | N2  | place | city | Köln         |
            | N3  | place | city | Gräfenroda   |
        When importing
        When geocoding "münster"
        Then the result set contains
            | object |
            | N1  |
        When geocoding "muenster"
        Then the result set contains
            | object |
            | N1  |
        When geocoding "munster"
        Then the result set contains
            | object |
            | N1  |
        When geocoding "Köln"
        Then the result set contains
            | object |
            | N2  |
        When geocoding "Koeln"
        Then the result set contains
            | object |
            | N2  |
        When geocoding "Koln"
        Then the result set contains
            | object |
            | N2  |
        When geocoding "gräfenroda"
        Then the result set contains
            | object |
            | N3  |
        When geocoding "graefenroda"
        Then the result set contains
            | object |
            | N3  |
        When geocoding "grafenroda"
        Then the result set contains
            | object |
            | N3  |

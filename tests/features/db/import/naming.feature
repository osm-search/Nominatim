@DB
Feature: Import and search of names
    Tests all naming related issues: normalisation,
    abbreviations, internationalisation, etc.


    Scenario: Case-insensitivity of search
        Given the place nodes
          | osm_id | class | type      | name
          | 1      | place | locality  | 'name' : 'FooBar'
        When importing
        Then table placex contains
          | object | class  | type     | name
          | N1     | place  | locality | 'name' : 'FooBar'
        When sending query "FooBar"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "foobar"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "fOObar"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "FOOBAR"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1

    Scenario: Multiple spaces in name
        Given the place nodes
          | osm_id | class | type      | name
          | 1      | place | locality  | 'name' : 'one two  three'
        When importing
        When sending query "one two three"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "one   two three"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "one two  three"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "    one two three"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1

    Scenario: Special characters in name
        Given the place nodes
          | osm_id | class | type      | name
          | 1      | place | locality  | 'name' : 'Jim-Knopf-Str'
          | 2      | place | locality  | 'name' : 'Smith/Weston'
          | 3      | place | locality  | 'name' : 'space mountain'
          | 4      | place | locality  | 'name' : 'space'
          | 5      | place | locality  | 'name' : 'mountain'
        When importing
        When sending query "Jim-Knopf-Str"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "Jim Knopf-Str"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "Jim Knopf Str"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "Jim/Knopf-Str"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "Jim-Knopfstr"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 1
        When sending query "Smith/Weston"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 2
        When sending query "Smith Weston"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 2
        When sending query "Smith-Weston"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 2
        When sending query "space mountain"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 3
        When sending query "space-mountain"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 3
        When sending query "space/mountain"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 3
        When sending query "space\mountain"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 3
        When sending query "space(mountain)"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | N        | 3

    Scenario: No copying name tag if only one name
        Given the place nodes
          | osm_id | class | type      | name              | geometry
          | 1      | place | locality  | 'name' : 'german' | country:de
        When importing
        Then table placex contains
          | object | calculated_country_code |
          | N1     | de
        And table placex contains as names for N1
          | object | k       | v
          | N1     | name    | german

    Scenario: Copying name tag to default language if it does not exist
        Given the place nodes
          | osm_id | class | type      | name                                     | geometry
          | 1      | place | locality  | 'name' : 'german', 'name:fi' : 'finnish' | country:de
        When importing
        Then table placex contains
          | object | calculated_country_code |
          | N1     | de
        And table placex contains as names for N1
          | k       | v
          | name    | german
          | name:fi | finnish
          | name:de | german

    Scenario: Copying default language name tag to name if it does not exist
        Given the place nodes
          | osm_id | class | type      | name                                        | geometry
          | 1      | place | locality  | 'name:de' : 'german', 'name:fi' : 'finnish' | country:de
        When importing
        Then table placex contains
          | object | calculated_country_code |
          | N1     | de
        And table placex contains as names for N1
          | k       | v
          | name    | german
          | name:fi | finnish
          | name:de | german

    Scenario: Do not overwrite default language with name tag
        Given the place nodes
          | osm_id | class | type      | name                                                          | geometry
          | 1      | place | locality  | 'name' : 'german', 'name:fi' : 'finnish', 'name:de' : 'local' | country:de
        When importing
        Then table placex contains
          | object | calculated_country_code |
          | N1     | de
        And table placex contains as names for N1
          | k       | v
          | name    | german
          | name:fi | finnish
          | name:de | local

    Scenario: Landuse without name are ignored
        Given the place areas
          | osm_type | osm_id | class    | type        | geometry
          | R        | 1      | natural  | meadow      | (0 0, 1 0, 1 1, 0 1, 0 0)
          | R        | 2      | landuse  | industrial  | (0 0, -1 0, -1 -1, 0 -1, 0 0)
        When importing
        Then table placex has no entry for R1
        And table placex has no entry for R2

    Scenario: Landuse with name are found
        Given the place areas
          | osm_type | osm_id | class    | type        | name                | geometry
          | R        | 1      | natural  | meadow      | 'name' : 'landuse1' | (0 0, 1 0, 1 1, 0 1, 0 0)
          | R        | 2      | landuse  | industrial  | 'name' : 'landuse2' | (0 0, -1 0, -1 -1, 0 -1, 0 0)
        When importing
        When sending query "landuse1"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | R        | 1
        When sending query "landuse2"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | R        | 2

    Scenario: Postcode boundaries without ref
        Given the place areas
          | osm_type | osm_id | class    | type        | postcode | geometry
          | R        | 1      | boundary | postal_code | 12345    | (0 0, 1 0, 1 1, 0 1, 0 0)
        When importing
        When sending query "12345"
        Then results contain
         | ID | osm_type | osm_id
         | 0  | R        | 1

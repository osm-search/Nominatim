@DB
Feature: Import and search of names
    Tests all naming related issues: normalisation,
    abbreviations, internationalisation, etc.

    Scenario: Case-insensitivity of search
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | FooBar |
        When importing
        Then placex contains
          | object | class  | type     | name+name |
          | N1     | place  | locality | FooBar |
        When searching for "FooBar"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "foobar"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "fOObar"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "FOOBAR"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |

    Scenario: Multiple spaces in name
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | one two  three |
        When importing
        When searching for "one two three"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "one   two three"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "one two  three"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "    one two three"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |

    Scenario: Special characters in name
        Given the places
          | osm | class | type      | name |
          | N1  | place | locality  | Jim-Knopf-Str |
          | N2  | place | locality  | Smith/Weston |
          | N3  | place | locality  | space mountain |
          | N4  | place | locality  | space |
          | N5  | place | locality  | mountain |
        When importing
        When searching for "Jim-Knopf-Str"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "Jim Knopf-Str"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "Jim Knopf Str"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "Jim/Knopf-Str"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "Jim-Knopfstr"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 1 |
        When searching for "Smith/Weston"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 2 |
        When searching for "Smith Weston"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 2 |
        When searching for "Smith-Weston"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 2 |
        When searching for "space mountain"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 3 |
        When searching for "space-mountain"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 3 |
        When searching for "space/mountain"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 3 |
        When searching for "space\mountain"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 3 |
        When searching for "space(mountain)"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | N        | 3 |

    Scenario: Landuse with name are found
        Given the places
          | osm | class    | type        | name     | geometry |
          | R1  | natural  | meadow      | landuse1 | (0 0, 1 0, 1 1, 0 1, 0 0) |
          | R2  | landuse  | industrial  | landuse2 | (0 0, -1 0, -1 -1, 0 -1, 0 0) |
        When importing
        When searching for "landuse1"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | R        | 1 |
        When searching for "landuse2"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | R        | 2 |

    @wip
    Scenario: Postcode boundaries without ref
        Given the places
          | osm | class    | type        | postcode | geometry |
          | R1  | boundary | postal_code | 12345    | (0 0, 1 0, 1 1, 0 1, 0 0) |
        When importing
        When searching for "12345"
        Then results contain
         | ID | osm_type | osm_id |
         | 0  | R        | 1 |

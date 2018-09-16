@APIDB
Feature: Places by osm_type and osm_id Tests
    Simple tests for errors in various response formats.

    Scenario Outline: Force error by providing too many ids
        When sending <format> lookup query for N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,N42,N43,N44,N45,N46,N47,N48,N49,N50,N51
        Then a <format> user error is returned

    Examples:
        | format  |
        | xml     |
        | json    |
        | geojson |

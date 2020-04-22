@APIDB
Feature: Reverse addressdetails
    Tests for addressdetails in reverse queries

    #github #1763
    Scenario: Correct translation of highways under construction
        When sending jsonv2 reverse coordinates -34.0290514,-53.5832235
        Then result addresses contain
        | road |
        | Ruta 9 Coronel Leonardo Olivera |

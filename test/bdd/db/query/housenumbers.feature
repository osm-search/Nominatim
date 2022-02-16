@DB
Feature: Searching of house numbers
    Test for specialised treeatment of housenumbers

    Background:
        Given the grid
         | 1 |   | 2 |   | 3 |
         |   | 9 |   |   |   |
         |   |   |   |   | 4 |


    Scenario: A simple ascii digit housenumber is found
        Given the places
         | osm | class    | type | housenr  | geometry |
         | N1  | building | yes  | 45       | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | North Road | 1,2,3    |
        When importing
        And sending search query "45, North Road"
        Then results contain
         | osm |
         | N1  |
        When sending search query "North Road 45"
        Then results contain
         | osm |
         | N1  |


    Scenario Outline: Numeral housenumbers in any script are found
        Given the places
         | osm | class    | type | housenr  | geometry |
         | N1  | building | yes  | <number> | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | North Road | 1,2,3    |
        When importing
        And sending search query "45, North Road"
        Then results contain
         | osm |
         | N1  |
        When sending search query "North Road ④⑤"
        Then results contain
         | osm |
         | N1  |
        When sending search query "North Road 𑁪𑁫"
        Then results contain
         | osm |
         | N1  |

    Examples:
        | number |
        | 45     |
        | ④⑤     |
        | 𑁪𑁫     |


    Scenario Outline: Each housenumber in a list is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnrs>  | 9        |
        And the places
         | osm | class   | type | name     | geometry |
         | W10 | highway | path | Multistr | 1,2,3    |
        When importing
        When sending search query "2 Multistr"
        Then results contain
         | osm |
         | N1  |
        When sending search query "4 Multistr"
        Then results contain
         | osm |
         | N1  |
        When sending search query "12 Multistr"
        Then results contain
         | osm |
         | N1  |

     Examples:
        | hnrs |
        | 2;4;12 |
        | 2,4,12 |
        | 2, 4, 12 |


    Scenario Outline: Housenumber - letter combinations are found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnr>   | 9        |
        And the places
         | osm | class   | type | name     | geometry |
         | W10 | highway | path | Multistr | 1,2,3    |
        When importing
        When sending search query "2A Multistr"
        Then results contain
         | osm |
         | N1  |
        When sending search query "2 a Multistr"
        Then results contain
         | osm |
         | N1  |
        When sending search query "2-A Multistr"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Multistr 2 A"
        Then results contain
         | osm |
         | N1  |

    Examples:
        | hnr |
        | 2a  |
        | 2 A |
        | 2-a |
        | 2/A |


    Scenario Outline: Number - Number combinations as a housenumber are found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnr>   | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | Chester St | 1,2,3    |
        When importing
        When sending search query "34-10 Chester St"
        Then results contain
         | osm |
         | N1  |
        When sending search query "34/10 Chester St"
        Then results contain
         | osm |
         | N1  |
        When sending search query "34 10 Chester St"
        Then results contain
         | osm |
         | N1  |
        When sending search query "3410 Chester St"
        Then results contain
         | osm |
         | W10 |

    Examples:
        | hnr   |
        | 34-10 |
        | 34 10 |
        | 34/10 |


    Scenario Outline: a bis housenumber is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnr>   | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | Rue Paris | 1,2,3    |
        When importing
        When sending search query "Rue Paris 45bis"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Rue Paris 45 BIS"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Rue Paris 45BIS"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Rue Paris 45 bis"
        Then results contain
         | osm |
         | N1  |

    Examples:
        | hnr   |
        | 45bis |
        | 45BIS |
        | 45 BIS |
        | 45 bis |

    Scenario Outline: a ter housenumber is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnr>   | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | Rue du Berger | 1,2,3    |
        When importing
        When sending search query "Rue du Berger 45ter"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Rue du Berger 45 TER"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Rue du Berger 45TER"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Rue du Berger 45 ter"
        Then results contain
         | osm |
         | N1  |

    Examples:
        | hnr   |
        | 45ter |
        | 45TER |
        | 45 ter |
        | 45 TER |


    Scenario Outline: a number - letter - number combination housenumber is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnr>   | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | Herengracht | 1,2,3    |
        When importing
        When sending search query "501-H 1 Herengracht"
        Then results contain
         | osm |
         | N1  |
        When sending search query "501H-1 Herengracht"
        Then results contain
         | osm |
         | N1  |
        When sending search query "501H1 Herengracht"
        Then results contain
         | osm |
         | N1  |
        When sending search query "501-H1 Herengracht"
        Then results contain
         | osm |
         | N1  |

    Examples:
        | hnr |
        | 501 H1 |
        | 501H 1 |
        | 501/H/1 |
        | 501h1 |


    Scenario Outline: Russian housenumbers are found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | <hnr>   | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | Голубинская улица | 1,2,3    |
        When importing
        When sending search query "Голубинская улица 55к3"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Голубинская улица 55 k3"
        Then results contain
         | osm |
         | N1  |
        When sending search query "Голубинская улица 55 к-3"
        Then results contain
         | osm |
         | N1  |

    Examples:
        | hnr |
        | 55к3 |
        | 55 к3 |


    Scenario: A name mapped as a housenumber is found
        Given the places
         | osm | class    | type | housenr | geometry |
         | N1  | building | yes  | Warring | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | Chester St | 1,2,3    |
        When importing
        When sending search query "Chester St Warring"
        Then results contain
         | osm |
         | N1  |


    Scenario: Interpolations are found according to their type
        Given the grid
         | 10  |  | 11  |
         | 100 |  | 101 |
         | 20  |  | 21  |
        And the places
         | osm  | class   | type        | name    | geometry |
         | W100 | highway | residential | Ringstr | 100, 101 |
        And the places
         | osm | class | type   | addr+interpolation | geometry |
         | W10 | place | houses | even               | 10, 11   |
         | W20 | place | houses | odd                | 20, 21   |
        And the places
         | osm | class | type  | housenr | geometry |
         | N10 | place | house | 10      | 10 |
         | N11 | place | house | 20      | 11 |
         | N20 | place | house | 11      | 20 |
         | N21 | place | house | 21      | 21 |
        And the ways
         | id | nodes |
         | 10 | 10, 11 |
         | 20 | 20, 21 |
        When importing
        When sending search query "Ringstr 12"
        Then results contain
         | osm |
         | W10 |
        When sending search query "Ringstr 13"
        Then results contain
         | osm |
         | W20 |

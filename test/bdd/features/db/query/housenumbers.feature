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
        And geocoding "45, North Road"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "North Road 45"
        Then the result set contains
         | object |
         | N1  |


    Scenario Outline: Numeral housenumbers in any script are found
        Given the places
         | osm | class    | type | housenr  | geometry |
         | N1  | building | yes  | <number> | 9        |
        And the places
         | osm | class   | type | name       | geometry |
         | W10 | highway | path | North Road | 1,2,3    |
        When importing
        And geocoding "45, North Road"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "North Road ④⑤"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "North Road 𑁪𑁫"
        Then the result set contains
         | object |
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
        When geocoding "2 Multistr"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "4 Multistr"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "12 Multistr"
        Then the result set contains
         | object |
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
        When geocoding "2A Multistr"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "2 a Multistr"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "2-A Multistr"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Multistr 2 A"
        Then the result set contains
         | object |
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
        When geocoding "34-10 Chester St"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "34/10 Chester St"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "34 10 Chester St"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "3410 Chester St"
        Then the result set contains
         | object |
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
        When geocoding "Rue Paris 45bis"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Rue Paris 45 BIS"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Rue Paris 45BIS"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Rue Paris 45 bis"
        Then the result set contains
         | object |
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
        When geocoding "Rue du Berger 45ter"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Rue du Berger 45 TER"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Rue du Berger 45TER"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Rue du Berger 45 ter"
        Then the result set contains
         | object |
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
        When geocoding "501-H 1 Herengracht"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "501H-1 Herengracht"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "501H1 Herengracht"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "501-H1 Herengracht"
        Then the result set contains
         | object |
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
        When geocoding "Голубинская улица 55к3"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Голубинская улица 55 k3"
        Then the result set contains
         | object |
         | N1  |
        When geocoding "Голубинская улица 55 к-3"
        Then the result set contains
         | object |
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
        When geocoding "Chester St Warring"
        Then the result set contains
         | object |
         | N1  |


    Scenario: A housenumber with interpolation is found
        Given the places
         | osm | class    | type | housenr | addr+interpolation | geometry |
         | N1  | building | yes  | 1-5     | odd                | 9        |
        And the places
         | osm | class   | type | name      | geometry |
         | W10 | highway | path | Rue Paris | 1,2,3    |
        When importing
        When geocoding "Rue Paris 1"
        Then the result set contains
         | object | address+house_number |
         | N1     | 1-5 |
        When geocoding "Rue Paris 3"
        Then the result set contains
         | object | address+house_number |
         | N1     | 1-5 |
        When geocoding "Rue Paris 5"
        Then the result set contains
         | object | address+house_number |
         | N1     | 1-5 |
        When geocoding "Rue Paris 2"
        Then the result set contains
         | object |
         | W10  |

    Scenario: A housenumber with bad interpolation is ignored
        Given the places
         | osm | class    | type | housenr | addr+interpolation | geometry |
         | N1  | building | yes  | 1-5     | bad                | 9        |
        And the places
         | osm | class   | type | name      | geometry |
         | W10 | highway | path | Rue Paris | 1,2,3    |
        When importing
        When geocoding "Rue Paris 1-5"
        Then the result set contains
         | object | address+house_number |
         | N1     | 1-5 |
        When geocoding "Rue Paris 3"
        Then the result set contains
         | object |
         | W10    |


    Scenario: A bad housenumber with a good interpolation is just a housenumber
        Given the places
         | osm | class    | type | housenr | addr+interpolation | geometry |
         | N1  | building | yes  | 1-100   | all                | 9        |
        And the places
         | osm | class   | type | name      | geometry |
         | W10 | highway | path | Rue Paris | 1,2,3    |
        When importing
        When geocoding "Rue Paris 1-100"
        Then the result set contains
         | object | address+house_number |
         | N1     | 1-100 |
        When geocoding "Rue Paris 3"
        Then the result set contains
         | object |
         | W10    |

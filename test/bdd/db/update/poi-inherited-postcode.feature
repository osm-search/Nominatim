@DB
Feature: Update of POI-inherited poscode
    Test updates of postcodes on street which was inherited from a related POI

    Background: Street and house with postcode
        Given the scene roads-with-pois
        And the places
         | osm | class | type  | housenr | postcode | street   | geometry |
         | N1  | place | house | 1       | 12345    | North St |:p-S1 |
        And the places
         | osm | class   | type        | name     | geometry |
         | W1  | highway | residential | North St | :w-north |
        When importing
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |

    Scenario: POI-inherited postcode remains when way type is changed
        When updating places
         | osm | class   | type         | name     | geometry |
         | W1  | highway | unclassified | North St | :w-north |
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |

    Scenario: POI-inherited postcode remains when way name is changed
        When updating places
         | osm | class   | type         | name     | geometry |
         | W1  | highway | unclassified | South St | :w-north |
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |

    Scenario: POI-inherited postcode remains when way geometry is changed
        When updating places
         | osm | class   | type         | name     | geometry |
         | W1  | highway | unclassified | South St | :w-south |
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |

    Scenario: POI-inherited postcode is added when POI postcode changes
        When updating places
         | osm | class | type  | housenr | postcode | street   | geometry |
         | N1  | place | house | 1       | 54321    | North St |:p-S1 |
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 54321 |

    Scenario: POI-inherited postcode remains when POI geometry changes
        When updating places
         | osm | class | type  | housenr | postcode | street   | geometry |
         | N1  | place | house | 1       | 12345    | North St |:p-S2 |
        Then search_name contains
         | object | nameaddress_vector |
         | W1     | 12345 |


Feature: Update of postcode only objects
    Tests that changes to objects containing only a postcode are
    propagated correctly.

    Scenario: Adding a postcode-only node
        When loading osm data
            """
            n1
            """
        Then place contains exactly
            | object |

        When updating osm data
            """
            n34 Tpostcode=4456
            """
        Then place_postcode contains exactly
            | object | postcode |
            | N34    | 4456     |
        And place contains exactly
            | object |


    Scenario: Deleting a postcode-only node
        When loading osm data
            """
            n34 Tpostcode=4456
            """
        Then place_postcode contains exactly
            | object | postcode |
            | N34    | 4456     |
        And place contains exactly
            | object |

        When updating osm data
            """
            n34 v2 dD
            """
        Then place contains exactly
            | object |
        And place_postcode contains exactly
            | object |


    Scenario Outline: Converting a regular object into a postcode-only node
        When loading osm data
            """
            n34 T<class>=<type>
            """
        Then place contains exactly
            | object | class   | type   |
            | N34    | <class> | <type> |

        When updating osm data
            """
            n34 Tpostcode=4456
            """
        Then place contains exactly
            | object |
        And place_postcode contains exactly
            | object | postcode |
            | N34    | 4456     |
        When indexing
        Then placex contains exactly
            | object |

        Examples:
            | class   | type       |
            | amenity | restaurant |
            | place   | hamlet     |


    Scenario Outline: Converting a postcode-only node into a regular object
        When loading osm data
            """
            n34 Tpostcode=4456
            """
        Then place_postcode contains exactly
            | object | postcode |
            | N34    | 4456     |

        When updating osm data
            """
            n34 T<class>=<type>
            """
        Then place contains exactly
            | object | class   | type   |
            | N34    | <class> | <type> |
        And place_postcode contains exactly
            | object |
        When indexing
        Then placex contains exactly
            | object | class   | type   |
            | N34    | <class> | <type> |

        Examples:
            | class   | type       |
            | amenity | restaurant |
            | place   | hamlet     |


    Scenario: Converting an interpolation into a postcode-only node
        Given the grid
            | 1 | 2 |
        When loading osm data
            """
            n1 Taddr:housenumber=3
            n2 Taddr:housenumber=17
            w34 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains exactly
            | object | class | type   |
            | N1     | place | house  |
            | N2     | place | house  |
            | W34    | place | houses |

        When updating osm data
            """
            w34 Tpostcode=4456 Nn1,n2
            """
        Then place contains exactly
            | object | class | type     |
            | N1     | place | house    |
            | N2     | place | house    |
        Then place_postcode contains exactly
            | object | postcode |
            | W34    | 4456     |
        When indexing
        Then location_property_osmline contains exactly
            | osm_id |


    Scenario: Converting a postcode-only node into an interpolation
        Given the grid
            | 1 | 2 |
        When loading osm data
            """
            n1 Taddr:housenumber=3
            n2 Taddr:housenumber=17
            w33 Thighway=residential Nn1,n2
            w34 Tpostcode=4456 Nn1,n2
            """
        Then place contains exactly
            | object | class   | type     |
            | N1     | place   | house    |
            | N2     | place   | house    |
            | W33    | highway | residential |
        And place_postcode contains exactly
            | object | postcode |
            | W34    | 4456     |

        When updating osm data
            """
            w34 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains exactly
            | object | class   | type   |
            | N1     | place   | house  |
            | N2     | place   | house  |
            | W33    | highway | residential |
            | W34    | place   | houses |
        And place_postcode contains exactly
            | object |
        When indexing
        Then location_property_osmline contains exactly
            | osm_id | startnumber | endnumber |
            | 34     | 5           | 15        |
        And placex contains exactly
            | object | class   | type   |
            | N1     | place   | house  |
            | N2     | place   | house  |
            | W33    | highway | residential |

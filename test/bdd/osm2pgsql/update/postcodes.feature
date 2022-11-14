@DB
Feature: Update of postcode only objects
    Tests that changes to objects containing only a postcode are
    propagated correctly.


    Scenario: Adding a postcode-only node
        When loading osm data
            """
            """
        Then place contains exactly
            | object |

        When updating osm data
            """
            n34 Tpostcode=4456
            """
        Then place contains exactly
            | object    | type     |
            | N34:place | postcode |
        When indexing
        Then placex contains exactly
            | object |


    Scenario: Deleting a postcode-only node
        When loading osm data
            """
            n34 Tpostcode=4456
            """
        Then place contains exactly
            | object    | type     |
            | N34:place | postcode |

        When updating osm data
            """
            n34 v2 dD
            """
        Then place contains exactly
            | object |
        When indexing
        Then placex contains exactly
            | object |


    Scenario Outline: Converting a regular object into a postcode-only node
        When loading osm data
            """
            n34 T<class>=<type>
            """
        Then place contains exactly
            | object      | type   |
            | N34:<class> | <type> |

        When updating osm data
            """
            n34 Tpostcode=4456
            """
        Then place contains exactly
            | object    | type     |
            | N34:place | postcode |
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
        Then place contains exactly
            | object    | type     |
            | N34:place | postcode |

        When updating osm data
            """
            n34 T<class>=<type>
            """
        Then place contains exactly
            | object      | type   |
            | N34:<class> | <type> |
        When indexing
        Then placex contains exactly
            | object      | type   |
            | N34:<class> | <type> |

        Examples:
            | class   | type       |
            | amenity | restaurant |
            | place   | hamlet     |


    Scenario: Converting na interpolation into a postcode-only node
        Given the grid
            | 1 | 2 |
        When loading osm data
            """
            n1 Taddr:housenumber=3
            n2 Taddr:housenumber=17
            w34 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains exactly
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
            | W34:place | houses |

        When updating osm data
            """
            w34 Tpostcode=4456 Nn1,n2
            """
        Then place contains exactly
            | object    | type     |
            | N1:place  | house    |
            | N2:place  | house    |
            | W34:place | postcode |
        When indexing
        Then location_property_osmline contains exactly
            | object |
        And placex contains exactly
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |


    Scenario: Converting a postcode-only node into an interpolation
        Given the grid
            | 1 | 2 |
        When loading osm data
            """
            n1 Taddr:housenumber=3
            n2 Taddr:housenumber=17
            w34 Tpostcode=4456 Nn1,n2
            """
        Then place contains exactly
            | object    | type     |
            | N1:place  | house    |
            | N2:place  | house    |
            | W34:place | postcode |

        When updating osm data
            """
            w34 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains exactly
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
            | W34:place | houses |
        When indexing
        Then location_property_osmline contains exactly
            | object |
            | 34:5   |
        And placex contains exactly
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |

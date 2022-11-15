@DB
Feature: Updates of address interpolation objects
    Test that changes to address interpolation objects are correctly
    propagated.

    Background:
        Given the grid
            | 1 | 2 |


    Scenario: Adding a new interpolation
        When loading osm data
            """
            n1 Taddr:housenumber=3
            n2 Taddr:housenumber=17
            """
        Then place contains
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |

        When updating osm data
            """
            w99 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
            | W99:place | houses |
        When indexing
        Then placex contains exactly
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
        Then location_property_osmline contains exactly
            | object |
            | 99:5   |


    Scenario: Delete an existing interpolation
        When loading osm data
            """
            n1 Taddr:housenumber=2
            n2 Taddr:housenumber=7
            w99 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
            | W99:place | houses |

        When updating osm data
            """
            w99 v2 dD
            """
        Then place contains
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
        When indexing
        Then placex contains exactly
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
        Then location_property_osmline contains exactly
            | object | indexed_status |


    Scenario: Changing an object to an interpolation
        When loading osm data
            """
            n1 Taddr:housenumber=3
            n2 Taddr:housenumber=17
            w99 Thighway=residential Nn1,n2
            """
        Then place contains
            | object      | type   |
            | N1:place    | house  |
            | N2:place    | house  |
            | W99:highway | residential  |

        When updating osm data
            """
            w99 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
            | W99:place | houses |
        When indexing
        Then placex contains exactly
            | object    | type   |
            | N1:place  | house  |
            | N2:place  | house  |
        And location_property_osmline contains exactly
            | object |
            | 99:5   |


    Scenario: Changing an interpolation to something else
        When loading osm data
            """
            n1 Taddr:housenumber=3
            n2 Taddr:housenumber=17
            w99 Taddr:interpolation=odd Nn1,n2
            """
        Then place contains
            | object      | type   |
            | N1:place    | house  |
            | N2:place    | house  |
            | W99:place | houses |

        When updating osm data
            """
            w99 Thighway=residential Nn1,n2
            """
        Then place contains
            | object      | type   |
            | N1:place    | house  |
            | N2:place    | house  |
            | W99:highway | residential  |
        When indexing
        Then placex contains exactly
            | object      | type   |
            | N1:place    | house  |
            | N2:place    | house  |
            | W99:highway | residential  |
        And location_property_osmline contains exactly
            | object |


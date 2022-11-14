@DB
Feature: Tag evaluation
    Tests if tags are correctly updated in the place table

    Background:
        Given the grid
            | 1  | 2  | 3 |
            | 10 | 11 |   |
            | 45 | 46 |   |

    Scenario: Main tag deleted
        When loading osm data
            """
            n1 Tamenity=restaurant
            n2 Thighway=bus_stop,railway=stop,name=X
            n3 Tamenity=prison
            """
        Then place contains exactly
            | object     | class   | type       |
            | N1         | amenity | restaurant |
            | N2:highway | highway | bus_stop   |
            | N2:railway | railway | stop       |
            | N3         | amenity | prison     |

        When updating osm data
            """
            n1 Tnot_a=restaurant
            n2 Thighway=bus_stop,name=X
            """
        Then place contains exactly
            | object     | class   | type       |
            | N2:highway | highway | bus_stop   |
            | N3         | amenity | prison     |
        And placex contains
            | object     | indexed_status |
            | N1:amenity | 100            |
            | N2:railway | 100            |
            | N3:amenity | 0              |


    Scenario: Main tag added
        When loading osm data
            """
            n1 Tatity=restaurant
            n2 Thighway=bus_stop,name=X
            """
        Then place contains exactly
            | object     | class   | type       |
            | N2:highway | highway | bus_stop   |

        When updating osm data
            """
            n1 Tamenity=restaurant
            n2 Thighway=bus_stop,railway=stop,name=X
            """
        Then place contains exactly
            | object     | class   | type       |
            | N1         | amenity | restaurant |
            | N2:highway | highway | bus_stop   |
            | N2:railway | railway | stop       |
        And placex contains
            | object     | indexed_status |
            | N1:amenity | 1              |
            | N2:railway | 1              |


    Scenario: Main tag modified
        When loading osm data
            """
            n10 Thighway=footway,name=X
            n11 Tamenity=atm
            """
        Then place contains exactly
            | object | class   | type    |
            | N10    | highway | footway |
            | N11    | amenity | atm     |

        When updating osm data
            """
            n10 Thighway=path,name=X
            n11 Thighway=primary
            """
        Then place contains exactly
            | object | class   | type    |
            | N10    | highway | path    |
            | N11    | highway | primary |
        And placex contains
            | object      | indexed_status |
            | N11:amenity | 100            |
            | N11:highway | 1              |


    Scenario: Main tags with name, name added
        When loading osm data
            """
            n45 Tlanduse=cemetry
            n46 Tbuilding=yes
            """
        Then place contains exactly
            | object | class   | type    |

        When updating osm data
            """
            n45 Tlanduse=cemetry,name=TODO
            n46 Tbuilding=yes,addr:housenumber=1
            """
        Then place contains exactly
            | object | class   | type    |
            | N45    | landuse | cemetry |
            | N46    | building| yes     |
        And placex contains exactly
            | object       | indexed_status |
            | N45:landuse  | 1              |
            | N46:building | 1              |


    Scenario: Main tags with name, name removed
        When loading osm data
            """
            n45 Tlanduse=cemetry,name=TODO
            n46 Tbuilding=yes,addr:housenumber=1
            """
        Then place contains exactly
            | object | class   | type    |
            | N45    | landuse | cemetry |
            | N46    | building| yes     |

        When updating osm data
            """
            n45 Tlanduse=cemetry
            n46 Tbuilding=yes
            """
        Then place contains exactly
            | object | class   | type    |
        And placex contains exactly
            | object       | indexed_status |
            | N45:landuse  | 100            |
            | N46:building | 100            |


    Scenario: Main tags with name, name modified
        When loading osm data
            """
            n45 Tlanduse=cemetry,name=TODO
            n46 Tbuilding=yes,addr:housenumber=1
            """
        Then place contains exactly
            | object | class   | type    | name            | address           |
            | N45    | landuse | cemetry | 'name' : 'TODO' | -                 |
            | N46    | building| yes     | -               | 'housenumber': '1'|

        When updating osm data
            """
            n45 Tlanduse=cemetry,name=DONE
            n46 Tbuilding=yes,addr:housenumber=10
            """
        Then place contains exactly
            | object | class   | type    | name            | address            |
            | N45    | landuse | cemetry | 'name' : 'DONE' | -                  |
            | N46    | building| yes     | -               | 'housenumber': '10'|
        And placex contains exactly
            | object       | indexed_status |
            | N45:landuse  | 2              |
            | N46:building | 2              |


    Scenario: Main tag added to address only node
        When loading osm data
            """
            n1 Taddr:housenumber=345
            """
        Then place contains exactly
            | object | class | type  | address |
            | N1     | place | house | 'housenumber': '345'|

        When updating osm data
            """
            n1 Taddr:housenumber=345,building=yes
            """
        Then place contains exactly
            | object | class    | type  | address |
            | N1     | building | yes   | 'housenumber': '345'|
        And placex contains exactly
            | object       | indexed_status |
            | N1:place     | 100            |
            | N1:building  | 1              |


    Scenario: Main tag removed from address only node
        When loading osm data
            """
            n1 Taddr:housenumber=345,building=yes
            """
        Then place contains exactly
            | object | class    | type  | address |
            | N1     | building | yes   | 'housenumber': '345'|

        When updating osm data
            """
            n1 Taddr:housenumber=345
            """
        Then place contains exactly
            | object | class | type  | address |
            | N1     | place | house | 'housenumber': '345'|
        And placex contains exactly
            | object       | indexed_status |
            | N1:place     | 1              |
            | N1:building  | 100            |


    Scenario: Main tags with name key, adding key name
        When loading osm data
            """
            n2 Tbridge=yes
            """
        Then place contains exactly
            | object | class    | type  |

        When updating osm data
            """
            n2 Tbridge=yes,bridge:name=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N2     | bridge   | yes   | 'name': 'high' |
        And placex contains exactly
            | object    | indexed_status |
            | N2:bridge | 1              |


    Scenario: Main tags with name key, deleting key name
        When loading osm data
            """
            n2 Tbridge=yes,bridge:name=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N2     | bridge   | yes   | 'name': 'high' |

        When updating osm data
            """
            n2 Tbridge=yes
            """
        Then place contains exactly
            | object | class    | type  |
        And placex contains exactly
            | object    | indexed_status |
            | N2:bridge | 100            |


    Scenario: Main tags with name key, changing key name
        When loading osm data
            """
            n2 Tbridge=yes,bridge:name=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N2     | bridge   | yes   | 'name': 'high' |

        When updating osm data
            """
            n2 Tbridge=yes,bridge:name:en=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N2     | bridge   | yes   | 'name:en': 'high' |
        And placex contains exactly
            | object    | indexed_status |
            | N2:bridge | 2              |


    Scenario: Downgrading a highway to one that is dropped without name
        When loading osm data
          """
          n100 x0 y0
          n101 x0.0001 y0.0001
          w1 Thighway=residential Nn100,n101
          """
        Then place contains exactly
          | object     |
          | W1:highway |

        When updating osm data
          """
          w1 Thighway=service Nn100,n101
          """
        Then place contains exactly
          | object     |
        And placex contains exactly
          | object     | indexed_status |
          | W1:highway | 100            |


    Scenario: Upgrading a highway to one that is not dropped without name
        When loading osm data
          """
          n100 x0 y0
          n101 x0.0001 y0.0001
          w1 Thighway=service Nn100,n101
          """
        Then place contains exactly
          | object     |

        When updating osm data
          """
          w1 Thighway=unclassified Nn100,n101
          """
        Then place contains exactly
          | object     |
          | W1:highway |
        And placex contains exactly
          | object     | indexed_status |
          | W1:highway | 1              |


    Scenario: Downgrading a highway when a second tag is present
        When loading osm data
          """
          n100 x0 y0
          n101 x0.0001 y0.0001
          w1 Thighway=residential,tourism=hotel Nn100,n101
          """
        Then place contains exactly
          | object     |
          | W1:highway |
          | W1:tourism |

        When updating osm data
          """
          w1 Thighway=service,tourism=hotel Nn100,n101
          """
        Then place contains exactly
          | object     |
          | W1:tourism |
        And placex contains exactly
          | object     |
          | W1:tourism |
          | W1:highway |
        And placex contains
          | object     | indexed_status |
          | W1:highway | 100            |


    Scenario: Upgrading a highway when a second tag is present
        When loading osm data
          """
          n100 x0 y0
          n101 x0.0001 y0.0001
          w1 Thighway=service,tourism=hotel Nn100,n101
          """
        Then place contains exactly
          | object     |
          | W1:tourism |

        When updating osm data
          """
          w1 Thighway=residential,tourism=hotel Nn100,n101
          """
        Then place contains exactly
          | object     |
          | W1:highway |
          | W1:tourism |
        And placex contains exactly
          | object     | indexed_status |
          | W1:tourism | 2              |
          | W1:highway | 1              |


    Scenario: Replay on administrative boundary
        When loading osm data
          """
          n10 x34.0 y-4.23
          n11 x34.1 y-4.23
          n12 x34.2 y-4.13
          w10 Tboundary=administrative,waterway=river,name=Border,admin_level=2 Nn12,n11,n10
          """
        Then place contains exactly
          | object       |
          | W10:waterway |
          | W10:boundary |

        When updating osm data
          """
          w10 Tboundary=administrative,waterway=river,name=Border,admin_level=2 Nn12,n11,n10
          """
        Then place contains exactly
          | object       |
          | W10:waterway |
          | W10:boundary |
        And placex contains exactly
          | object       |
          | W10:waterway |


    Scenario: Change admin_level on administrative boundary
        When loading osm data
          """
          n10 x34.0 y-4.23
          n11 x34.1 y-4.23
          n12 x34.2 y-4.13
          w10 Tboundary=administrative,name=Border,admin_level=2 Nn12,n11,n10
          """
        Then place contains exactly
          | object       | admin_level |
          | W10:boundary | 2           |

        When updating osm data
          """
          w10 Tboundary=administrative,name=Border,admin_level=4 Nn12,n11,n10
          """
        Then place contains exactly
          | object       | admin_level |
          | W10:boundary | 4           |

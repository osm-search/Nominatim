@DB
Feature: Tag evaluation
    Tests if tags are correctly updated in the place table


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


    Scenario: Main tags with name key, adding key name
        When loading osm data
            """
            n22 Tbridge=yes
            """
        Then place contains exactly
            | object | class    | type  |

        When updating osm data
            """
            n22 Tbridge=yes,bridge:name=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N22    | bridge   | yes   | 'name': 'high' |


    Scenario: Main tags with name key, deleting key name
        When loading osm data
            """
            n22 Tbridge=yes,bridge:name=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N22    | bridge   | yes   | 'name': 'high' |

        When updating osm data
            """
            n22 Tbridge=yes
            """
        Then place contains exactly
            | object | class    | type  |


    Scenario: Main tags with name key, changing key name
        When loading osm data
            """
            n22 Tbridge=yes,bridge:name=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N22    | bridge   | yes   | 'name': 'high' |

        When updating osm data
            """
            n22 Tbridge=yes,bridge:name:en=high
            """
        Then place contains exactly
            | object | class    | type  | name           |
            | N22    | bridge   | yes   | 'name:en': 'high' |


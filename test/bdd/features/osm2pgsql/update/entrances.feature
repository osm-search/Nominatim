Feature: Update of entrance objects by osm2pgsql
    Testing of correct update of the entrance table

    Scenario: A new entrance is added
        When loading osm data
          """
          n1 Tshop=shoes
          """
        Then place_entrance contains exactly
          | osm_id |
        When updating osm data
          """
          n2 Tentrance=yes
          """
        Then place_entrance contains exactly
          | osm_id | type |
          | 2      | yes  |

    Scenario: An existing entrance is deleted
        When loading osm data
          """
          n1 Tentrance=yes
          """
        Then place_entrance contains exactly
          | osm_id | type |
          | 1      | yes  |
        When updating osm data
          """
          n1 dD
          """
        Then place_entrance contains exactly
          | osm_id |

    Scenario: An existing node becomes an entrance
        When loading osm data
          """
          n1 Tshop=sweets
          """
        Then place_entrance contains exactly
          | osm_id | type |
        And place contains exactly
          | object | class |
          | N1     | shop  |
        When updating osm data
          """
          n1 Tshop=sweets,entrance=yes
          """
        Then place_entrance contains exactly
          | osm_id | type |
          | 1      | yes  |
        And place contains exactly
          | object | class |
          | N1     | shop  |

    Scenario: An existing entrance tag is removed
        When loading osm data
          """
          n1 Tshop=sweets,entrance=yes
          """
        Then place_entrance contains exactly
          | osm_id | type |
          | 1      | yes  |
        And place contains exactly
          | object | class |
          | N1     | shop  |
        When updating osm data
          """
          n1 Tshop=sweets
          """
        Then place_entrance contains exactly
          | osm_id | type |
        And place contains exactly
          | object | class |
          | N1     | shop  |

    Scenario: Extratags are added to an entrance
        When loading osm data
          """
          n1 Tentrance=yes
          """
        Then place_entrance contains exactly
          | osm_id | type | extratags |
          | 1      | yes  | -         |
        When updating osm data
          """
          n1 Tentrance=yes,access=yes
          """
        Then place_entrance contains exactly
          | osm_id | type | extratags!dict  |
          | 1      | yes  | 'access': 'yes' |

    Scenario: Extratags are deleted from an entrance
        When loading osm data
          """
          n1 Tentrance=yes,access=yes
          """
        Then place_entrance contains exactly
          | osm_id | type | extratags!dict  |
          | 1      | yes  | 'access': 'yes' |
        When updating osm data
          """
          n1 Tentrance=yes
          """
        Then place_entrance contains exactly
          | osm_id | type | extratags |
          | 1      | yes  | -         |

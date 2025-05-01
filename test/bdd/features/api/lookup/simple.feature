Feature: Tests for finding places by osm_type and osm_id
    Simple tests for response format.

    Scenario Outline: Address lookup for existing object
        When sending v1/lookup with format <format>
          | osm_ids |
          | N5484325405,W43327921,,R123924,X99,N0 |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And exactly 3 results are returned

    Examples:
        | format      | outformat   |
        | xml         | xml         |
        | json        | json        |
        | jsonv2      | json        |
        | geojson     | geojson     |
        | geocodejson | geocodejson |

    Scenario: Address lookup for non-existing or invalid object
        When sending v1/lookup
          | osm_ids |
          | X99,,N0,nN158845944,ABC,,W9 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And exactly 0 results are returned

    Scenario Outline: Boundingbox is returned
        When sending v1/lookup with format <format>
          | osm_ids |
          | N5484325405,W43327921 |
        Then the result is valid <outformat>
        And the result set contains exactly
          | object      | boundingbox!in_box |
          | N5484325405 | 47.135,47.14,9.52,9.525 |
          | W43327921   | 47.07,47.08,9.50,9.52   |

    Examples:
        | format      | outformat   |
        | xml         | xml         |
        | json        | json        |
        | jsonv2      | json        |
        | geojson     | geojson     |

    Scenario: Linked places return information from the linkee
        When sending v1/lookup with format geocodejson
          | osm_ids |
          | N1932181216 |
        Then the result is valid geocodejson
        And exactly 1 result is returned
        And all results contain
          | name  |
          | Vaduz |

    Scenario Outline: Force error by providing too many ids
        When sending v1/lookup with format <format>
          | osm_ids |
          | N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11,N12,N13,N14,N15,N16,N17,N18,N19,N20,N21,N22,N23,N24,N25,N26,N27,N28,N29,N30,N31,N32,N33,N34,N35,N36,N37,N38,N39,N40,N41,N42,N43,N44,N45,N46,N47,N48,N49,N50,N51 |
        Then a HTTP 400 is returned
        And the result is valid <outformat>
        And the result contains
          | error+code | error+message |
          | 400        | Too many object IDs. |

    Examples:
        | format      | outformat   |
        | xml         | xml         |
        | json        | json        |
        | jsonv2      | json        |
        | geojson     | json        |
        | geocodejson | json        |

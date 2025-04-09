Feature: Search queries
    Testing different queries and parameters

    Scenario: Simple XML search
        When sending v1/search with format xml
          | q |
          | Schaan |
        Then a HTTP 200 is returned
        And the result is valid xml
        And all results have attributes place_id,osm_type,osm_id
        And all results have attributes place_rank,boundingbox
        And all results have attributes lat,lon,display_name
        And all results have attributes class,type,importance
        And all results have no attributes address
        And all results contain
          | boundingbox!in_box |
          | 46.5,47.5,9,10 |

    Scenario Outline: Simple JSON search
        When sending v1/search with format <format>
          | q |
          | Vaduz |
        Then a HTTP 200 is returned
        And the result is valid json
        And all results have attributes place_id,licence,<cname>,type
        And all results have attributes osm_type,osm_id,boundingbox
        And all results have attributes lat,lon,display_name,importance
        And all results have no attributes address
        And all results contain
          | boundingbox!in_box |
          | 46.5,47.5,9,10 |

        Examples:
          | format | cname    |
          | json   | class    |
          | jsonv2 | category |

    Scenario: Unknown formats returns a user error
        When sending v1/search with format x45
          | q |
          | Vaduz |
        Then a HTTP 400 is returned

    Scenario Outline: Search with addressdetails
        When sending v1/search with format <format>
          | q       | addressdetails |
          | Triesen | 1 |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And result 0 contains in field address
          | param        | value |
          | village      | Triesen |
          | county       | Oberland |
          | postcode     | 9495 |
          | country      | Liechtenstein |
          | country_code | li |
          | ISO3166-2-lvl8 | LI-09 |

        Examples:
          | format | outformat |
          | json   | json |
          | jsonv2 | json |
          | geojson | geojson |
          | xml    | xml |

    Scenario: Coordinate search with addressdetails
        When geocoding "47.12400621,9.6047552"
          | accept-language |
          | en |
        Then all results contain
          | display_name |
          | Guschg, Valorschstrasse, Balzers, Oberland, 9497, Liechtenstein |

    Scenario: Address details with unknown class types
        When geocoding "Kloster St. Elisabeth"
        Then result 0 contains
          | category | type      | address+amenity |
          | amenity  | monastery | Kloster St. Elisabeth |

    Scenario: Disabling deduplication
        When geocoding "Malbunstr, Schaan"
        Then exactly 1 result is returned
        When geocoding "Malbunstr, Schaan"
          | dedupe |
          | 0 |
        Then exactly 4 results are returned

    Scenario: Search with bounded viewbox in right area
        When geocoding "post"
          | bounded | viewbox |
          | 1       |  9,47,10,48 |
        Then result 0 contains
          | address+town |
          | Vaduz |
        When geocoding "post"
          | bounded | viewbox |
          | 1       |  9.49712,47.17122,9.52605,47.16242 |
        Then result 0 contains
          | address+town |
          | Schaan |

    Scenario: Country search with bounded viewbox remain in the area
        When geocoding
          | bounded | viewbox                           | country |
          | 1       | 9.49712,47.17122,9.52605,47.16242 | de |
        Then exactly 0 results are returned

    Scenario: Search with bounded viewboxlbrt in right area
        When geocoding "bar"
          | bounded | viewboxlbrt |
          | 1       | 9.49712,47.16242,9.52605,47.17122 |
        Then all results contain
          | address+town |
          | Schaan |

    Scenario: No POI search with unbounded viewbox
        When geocoding "restaurant"
          | viewbox |
          | 9.93027,53.61634,10.10073,53.54500 |
        Then all results contain
          | display_name!fm |
          | .*[Rr]estaurant.* |

    Scenario: bounded search remains within viewbox, even with no results
         When geocoding "[restaurant]"
           | bounded | viewbox |
           | 1       | 43.5403125,-5.6563282,43.54285,-5.662003 |
        Then exactly 0 results are returned

    Scenario: bounded search remains within viewbox with results
        When geocoding "restaurant"
         | bounded | viewbox |
         | 1       | 9.49712,47.17122,9.52605,47.16242 |
        Then all results contain
         | boundingbox!in_box |
         | 47.16242,47.17122,9.49712,9.52605 |

    Scenario: Prefer results within viewbox
        When geocoding "Gässle"
          | accept-language | viewbox |
          | en              | 9.52413,47.10759,9.53140,47.10539 |
        Then result 0 contains
          | address+village |
          | Triesen |
        When geocoding "Gässle"
          | accept-language | viewbox |
          | en              | 9.45949,47.08421,9.54094,47.05466 |
        Then result 0 contains
          | address+town |
          | Balzers |

    Scenario: viewboxes cannot be points
        When sending v1/search
          | q   | viewbox |
          | foo | 1.01,34.6,1.01,34.6 |
        Then a HTTP 400 is returned

    Scenario Outline: viewbox must have four coordinate numbers
        When sending v1/search
          | q   | viewbox |
          | foo | <viewbox> |
        Then a HTTP 400 is returned

    Examples:
        | viewbox |
        | 34      |
        | 0.003,-84.4 |
        | 5.2,4.5542,12.4 |
        | 23.1,-6,0.11,44.2,9.1 |

    Scenario Outline: viewboxlbrt must have four coordinate numbers
        When sending v1/search
          | q   | viewboxlbrt |
          | foo | <viewbox> |
        Then a HTTP 400 is returned

    Examples:
        | viewbox |
        | 34      |
        | 0.003,-84.4 |
        | 5.2,4.5542,12.4 |
        | 23.1,-6,0.11,44.2,9.1 |

    Scenario: Overly large limit number for search results
        When geocoding "restaurant"
          | limit |
          | 1000 |
        Then exactly 35 results are returned

    Scenario: Limit number of non-duplicated search results
        When geocoding "landstr"
          | dedupe |
          | 0      |
        Then exactly 10 results are returned
        When geocoding "landstr"
          | limit | dedupe |
          | 4     | 0      |
        Then exactly 4 results are returned

    Scenario: Limit parameter must be a number
        When sending v1/search
          | q           | limit |
          | Blue Laguna | );    |
        Then a HTTP 400 is returned

    Scenario: Restrict to feature type country
        When geocoding "fürstentum"
          | featureType |
          | country |
        Then all results contain
          | place_rank |
          | 4 |

    Scenario: Restrict to feature type state
        When geocoding "Wangerberg"
        Then more than 0 results are returned
        When geocoding "Wangerberg"
          | featureType |
          | state |
        Then exactly 0 results are returned

    Scenario: Restrict to feature type city
        When geocoding "vaduz"
          | featureType |
          | state |
        Then exactly 0 results are returned
        When geocoding "vaduz"
          | featureType |
          | city |
        Then more than 0 results are returned
        Then all results contain
          | place_rank |
          | 16 |

    Scenario: Restrict to feature type settlement
        When geocoding "Malbun"
        Then result 1 contains
          | category |
          | landuse |
        When geocoding "Malbun"
          | featureType |
          | settlement |
        Then all results contain
          | category | type |
          | place    | village |

    Scenario Outline: Search with polygon threshold (json)
        When sending v1/search with format json
          | q           | polygon_geojson | polygon_threshold |
          | Triesenberg | 1               | <th> |
        Then a HTTP 200 is returned
        And the result is valid json
        And more than 0 results are returned
        And all results have attributes geojson

        Examples:
          | th |
          | -1 |
          | 0.0 |
          | 0.5 |
          | 999 |

    Scenario Outline: Search with polygon threshold (xml)
        When sending v1/search with format xml
          | q           | polygon_geojson | polygon_threshold |
          | Triesenberg | 1               | <th> |
        Then a HTTP 200 is returned
        And the result is valid xml
        And more than 0 results are returned
        And all results have attributes geojson

        Examples:
          | th |
          | -1 |
          | 0.0 |
          | 0.5 |
          | 999 |

    Scenario Outline: Search with invalid polygon threshold (xml)
        When sending v1/search with format xml
          | q           | polygon_geojson | polygon_threshold |
          | Triesenberg | 1               | <th> |
        Then a HTTP 400 is returned

        Examples:
          | th |
          | x |
          | ;; |
          | 1m |

    Scenario Outline: Search with extratags
        When sending v1/search with format <format>
          | q       | extratags |
          | Landstr | 1 |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And more than 0 results are returned
        Then all results have attributes extratags

        Examples:
          | format | outformat |
          | xml    | xml |
          | json   | json |
          | jsonv2 | json |
          | geojson | geojson |

    Scenario Outline: Search with namedetails
        When sending v1/search with format <format>
          | q       | namedetails |
          | Landstr | 1 |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And more than 0 results are returned
        Then all results have attributes namedetails

        Examples:
          | format | outformat |
          | xml    | xml |
          | json   | json |
          | jsonv2 | json |
          | geojson | geojson |

    Scenario Outline: Search result with contains formatted geometry
        When sending v1/search with format <format>
          | q           | <param> |
          | Triesenberg | 1 |
        Then a HTTP 200 is returned
        And the result is valid <outformat>
        And more than 0 results are returned
        And all results have attributes <response_attribute>

        Examples:
          | format   | outformat | param        | response_attribute |
          | xml      | xml       | polygon_text | geotext |
          | json     | json      | polygon_text | geotext |
          | jsonv2   | json      | polygon_text | geotext |
          | xml      | xml       |  polygon_svg | geosvg |
          | json     | json      |  polygon_svg | svg |
          | jsonv2   | json      |  polygon_svg | svg |
          | xml      | xml       | polygon_kml  | geokml |
          | json     | json      | polygon_kml  | geokml |
          | jsonv2   | json      | polygon_kml  | geokml |
          | xml      | xml       | polygon_geojson | geojson |
          | json     | json      | polygon_geojson | geojson |
          | jsonv2   | json      | polygon_geojson | geojson |
          | geojson  | geojson   | polygon_geojson | geojson |

    Scenario Outline: Search result in geojson format contains no non-geojson geometry
        When sending v1/search with format geojson
          | q           | <param> |
          | Triesenberg | 1 |
        Then a HTTP 200 is returned
        And the result is valid geojson
        And more than 0 results are returned
        And all results have no attributes <response_attribute>

        Examples:
          | param        | response_attribute |
          | polygon_text | geotext            |
          | polygon_svg  | svg                |
          | polygon_kml  | geokml             |

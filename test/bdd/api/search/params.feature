@APIDB
Feature: Search queries
    Testing different queries and parameters

    Scenario: Simple XML search
        When sending xml search query "Schaan"
        Then result 0 has attributes place_id,osm_type,osm_id
        And result 0 has attributes place_rank,boundingbox
        And result 0 has attributes lat,lon,display_name
        And result 0 has attributes class,type,importance
        And result 0 has not attributes address
        And result 0 has bounding box in 46.5,47.5,9,10

    Scenario: Simple JSON search
        When sending json search query "Vaduz"
        Then result 0 has attributes place_id,licence,class,type
        And result 0 has attributes osm_type,osm_id,boundingbox
        And result 0 has attributes lat,lon,display_name,importance
        And result 0 has not attributes address
        And result 0 has bounding box in 46.5,47.5,9,10

    Scenario: Unknown formats returns a user error
        When sending search query "Vaduz"
          | format |
          | x45    |
        Then a HTTP 400 is returned

    Scenario Outline: Search with addressdetails
        When sending <format> search query "Triesen" with address
        Then address of result 0 is
          | type         | value |
          | village      | Triesen |
          | county       | Oberland |
          | postcode     | 9495 |
          | country      | Liechtenstein |
          | country_code | li |
          | ISO3166-2-lvl8 | LI-09 |

    Examples:
          | format |
          | json   |
          | jsonv2 |
          | geojson |
          | xml |

    Scenario: Coordinate search with addressdetails
        When sending json search query "47.12400621,9.6047552"
          | accept-language |
          | en |
        Then results contain
          | display_name |
          | Guschg, Valorschstrasse, Balzers, Oberland, 9497, Liechtenstein |

    Scenario: Address details with unknown class types
        When sending json search query "Kloster St. Elisabeth" with address
        Then results contain
          | ID | class   | type |
          | 0  | amenity | monastery |
        And result addresses contain
          | ID | amenity |
          | 0  | Kloster St. Elisabeth |

    Scenario: Disabling deduplication
        When sending json search query "Malbunstr"
        Then there are no duplicates
        When sending json search query "Malbunstr"
          | dedupe |
          | 0 |
        Then there are duplicates

    Scenario: Search with bounded viewbox in right area
        When sending json search query "bar" with address
          | bounded | viewbox |
          | 1       |  9,47,10,48 |
        Then result addresses contain
          | ID | town |
          | 0  | Vaduz |
        When sending json search query "bar" with address
          | bounded | viewbox |
          | 1       |  9.49712,47.17122,9.52605,47.16242 |
        Then result addresses contain
          | town |
          | Schaan |

    Scenario: Country search with bounded viewbox remain in the area
        When sending json search query "" with address
          | bounded | viewbox                                 | country |
          | 1       | 9.49712,47.17122,9.52605,47.16242 | de |
        Then less than 1 result is returned

    Scenario: Search with bounded viewboxlbrt in right area
        When sending json search query "bar" with address
          | bounded | viewboxlbrt |
          | 1       | 9.49712,47.16242,9.52605,47.17122 |
        Then result addresses contain
          | town |
          | Schaan |

    @Fail
    Scenario: No POI search with unbounded viewbox
        When sending json search query "restaurant"
          | viewbox |
          | 9.93027,53.61634,10.10073,53.54500 |
        Then results contain
          | display_name |
          | ^[^,]*[Rr]estaurant.* |

    Scenario: bounded search remains within viewbox, even with no results
         When sending json search query "[restaurant]"
           | bounded | viewbox |
           | 1       | 43.5403125,-5.6563282,43.54285,-5.662003 |
        Then less than 1 result is returned

    Scenario: bounded search remains within viewbox with results
        When sending json search query "restaurant"
         | bounded | viewbox |
         | 1       | 9.49712,47.17122,9.52605,47.16242 |
        Then result has centroid in 9.49712,47.16242,9.52605,47.17122

    Scenario: Prefer results within viewbox
        When sending json search query "Gässle" with address
          | accept-language |
          | en |
        Then result addresses contain
          | ID | town |
          | 0  | Balzers |
        When sending json search query "Gässle" with address
          | accept-language | viewbox |
          | en              | 9.52413,47.10759,9.53140,47.10539 |
        Then result addresses contain
          | ID | village |
          | 0  | Triesen |

    Scenario: viewboxes cannot be points
        When sending json search query "foo"
          | viewbox |
          | 1.01,34.6,1.01,34.6 |
        Then a HTTP 400 is returned

    Scenario Outline: viewbox must have four coordinate numbers
        When sending json search query "foo"
          | viewbox |
          | <viewbox> |
        Then a HTTP 400 is returned

    Examples:
        | viewbox |
        | 34      |
        | 0.003,-84.4 |
        | 5.2,4.5542,12.4 |
        | 23.1,-6,0.11,44.2,9.1 |

    Scenario Outline: viewboxlbrt must have four coordinate numbers
        When sending json search query "foo"
          | viewboxlbrt |
          | <viewbox> |
        Then a HTTP 400 is returned

    Examples:
        | viewbox |
        | 34      |
        | 0.003,-84.4 |
        | 5.2,4.5542,12.4 |
        | 23.1,-6,0.11,44.2,9.1 |

    Scenario: Overly large limit number for search results
        When sending json search query "restaurant"
          | limit |
          | 1000 |
        Then at most 50 results are returned

    Scenario: Limit number of search results
        When sending json search query "landstr"
        Then more than 4 results are returned
        When sending json search query "landstr"
          | limit |
          | 4 |
        Then exactly 4 results are returned

    Scenario: Limit parameter must be a number
        When sending search query "Blue Laguna"
          | limit |
          | );    |
        Then a HTTP 400 is returned

    Scenario: Restrict to feature type country
        When sending xml search query "fürstentum"
        Then results contain
          | ID | class |
          | 1  | building |
        When sending xml search query "fürstentum"
          | featureType |
          | country |
        Then results contain
          | place_rank |
          | 4 |

    Scenario: Restrict to feature type state
        When sending xml search query "Wangerberg"
        Then more than 1 result is returned
        When sending xml search query "Wangerberg"
          | featureType |
          | state |
        Then exactly 0 results are returned

    Scenario: Restrict to feature type city
        When sending xml search query "vaduz"
        Then results contain
          | ID | place_rank |
          | 1  | 30 |
        When sending xml search query "vaduz"
          | featureType |
          | city |
        Then results contain
          | place_rank |
          | 16 |

    Scenario: Restrict to feature type settlement
        When sending json search query "Malbun"
        Then results contain
          | ID | class |
          | 1  | landuse |
        When sending json search query "Malbun"
          | featureType |
          | settlement |
        Then results contain
          | class | type |
          | place | village |

    Scenario Outline: Search with polygon threshold (json)
        When sending json search query "triesenberg"
          | polygon_geojson | polygon_threshold |
          | 1               | <th> |
        Then at least 1 result is returned
        And result 0 has attributes geojson

     Examples:
        | th |
        | -1 |
        | 0.0 |
        | 0.5 |
        | 999 |

    Scenario Outline: Search with polygon threshold (xml)
        When sending xml search query "triesenberg"
          | polygon_geojson | polygon_threshold |
          | 1               | <th> |
        Then at least 1 result is returned
        And result 0 has attributes geojson

     Examples:
        | th |
        | -1 |
        | 0.0 |
        | 0.5 |
        | 999 |

    Scenario Outline: Search with invalid polygon threshold (xml)
        When sending xml search query "triesenberg"
          | polygon_geojson | polygon_threshold |
          | 1               | <th> |
        Then a HTTP 400 is returned

     Examples:
        | th |
        | x |
        | ;; |
        | 1m |

    Scenario Outline: Search with extratags
        When sending <format> search query "Landstr"
          | extratags |
          | 1 |
        Then result has attributes extratags

    Examples:
        | format |
        | xml |
        | json |
        | jsonv2 |
        | geojson |

    Scenario Outline: Search with namedetails
        When sending <format> search query "Landstr"
          | namedetails |
          | 1 |
        Then result has attributes namedetails

    Examples:
        | format |
        | xml |
        | json |
        | jsonv2 |
        | geojson |

    Scenario Outline: Search result with contains TEXT geometry
        When sending <format> search query "triesenberg"
          | polygon_text |
          | 1 |
        Then result has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geotext |
        | json     | geotext |
        | jsonv2   | geotext |

    Scenario Outline: Search result contains SVG geometry
        When sending <format> search query "triesenberg"
          | polygon_svg |
          | 1 |
        Then result has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geosvg |
        | json     | svg |
        | jsonv2   | svg |

    Scenario Outline: Search result contains KML geometry
        When sending <format> search query "triesenberg"
          | polygon_kml |
          | 1 |
        Then result has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geokml |
        | json     | geokml |
        | jsonv2   | geokml |

    Scenario Outline: Search result contains GEOJSON geometry
        When sending <format> search query "triesenberg"
          | polygon_geojson |
          | 1 |
        Then result has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geojson |
        | json     | geojson |
        | jsonv2   | geojson |
        | geojson  | geojson |

    Scenario Outline: Search result in geojson format contains no non-geojson geometry
        When sending geojson search query "triesenberg"
          | polygon_text | polygon_svg | polygon_geokml |
          | 1            | 1           | 1              |
        Then result 0 has not attributes <response_attribute>

    Examples:
        | response_attribute |
        | geotext            |
        | polygonpoints      |
        | svg                |
        | geokml             |

    Scenario: Search along a route
        When sending json search query "rathaus" with address
        Then result addresses contain
          | ID | town |
          | 0  | Schaan |
        When sending json search query "rathaus" with address
          | bounded | routewidth | route                              |
          | 1       | 0.1        |  9.54353,47.11772,9.54314,47.11894 |
        Then result addresses contain
          | town |
          | Triesenberg |


    Scenario: Array parameters are ignored
        When sending json search query "Vaduz" with address
          | countrycodes[] | polygon_svg[] | limit[] | polygon_threshold[] |
          | IT             | 1             | 3       | 3.4                 |
        Then result addresses contain
          | ID | country_code |
          | 0  | li           |

Feature: Geocodejson for Reverse API
    Testing correctness of geocodejson output (API version v1).

    Scenario Outline: Reverse geocodejson - Simple with no results
        When sending v1/reverse with format geocodejson
          | lat   | lon   |
          | <lat> | <lon> |
        Then a HTTP 200 is returned
        And the result is valid json
        And the result contains
          | error |
          | Unable to geocode |

        Examples:
          | lat  | lon |
          | 0.0  | 0.0 |
          | 91.3 | 0.4    |
          | -700 | 0.4    |
          | 0.2  | 324.44 |
          | 0.2  | -180.4 |

    Scenario Outline: Reverse geocodejson - Simple OSM result
        When sending v1/reverse with format geocodejson
          | lat    | lon   | addressdetails |
          | 47.066 | 9.504 | <has_address>  |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And the result metadata contains
          | version | licence | attribution!fm |
          | 0.1.0   | ODbL    | Data © OpenStreetMap contributors, ODbL 1.0. https?://osm.org/copyright |
        And all results have <attributes> country,postcode,county,city,district,street,housenumber,admin
        And all results contain
          | param               | value |
          | osm_type            | node |
          | osm_id              | 6522627624 |
          | osm_key             | shop |
          | osm_value           | bakery |
          | type                | house |
          | name                | Dorfbäckerei Herrmann |
          | label               | Dorfbäckerei Herrmann, 29, Gnetsch, Mäls, Balzers, Oberland, 9496, Liechtenstein |
          | geojson+type        | Point |
          | geojson+coordinates | [9.5036065, 47.0660892] |

        Examples:
          | has_address | attributes     |
          | 1           | attributes     |
          | 0           | no attributes |

    Scenario: Reverse geocodejson - City housenumber-level address with street
        When sending v1/reverse with format geocodejson
          | lat        | lon        |
          | 47.1068011 | 9.52810091 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
          | housenumber | street    | postcode | city    | country |
          | 8           | Im Winkel | 9495     | Triesen | Liechtenstein |
         And all results contain
          | admin+level6 | admin+level8 |
          | Oberland     | Triesen      |

    Scenario: Reverse geocodejson - Town street-level address with street
        When sending v1/reverse with format geocodejson
          | lat    | lon   | zoom |
          | 47.066 | 9.504 | 16 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
          | name    | city    | postcode | country |
          | Gnetsch | Balzers | 9496     | Liechtenstein |

    Scenario: Reverse geocodejson - Poi street-level address with footway
        When sending v1/reverse with format geocodejson
          | lat      | lon     |
          | 47.06515 | 9.50083 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
          | street  | city    | postcode | country |
          | Burgweg | Balzers | 9496     | Liechtenstein |

    Scenario: Reverse geocodejson - City address with suburb
        When sending v1/reverse with format geocodejson
          | lat       | lon      |
          | 47.146861 | 9.511771 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
          | housenumber | street   | district | city  | postcode | country |
          | 5           | Lochgass | Ebenholz | Vaduz | 9490     | Liechtenstein |

    Scenario: Reverse geocodejson - Tiger address
        When sending v1/reverse with format geocodejson
          | lat           | lon            |
          | 32.4752389363 | -86.4810198619 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
         | osm_type | osm_id    | osm_key | osm_value | type  |
         | way      | 396009653 | place   | house     | house |
        And all results contain
         | housenumber | street              | city       | county         | postcode | country       |
         | 707         | Upper Kingston Road | Prattville | Autauga County | 36067    | United States |

    Scenario: Reverse geocodejson - Interpolation address
        When sending v1/reverse with format geocodejson
          | lat       | lon        |
          | 47.118533 | 9.57056562 |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
          | osm_type | osm_id | osm_key | osm_value | type  |
          | way      | 1      | place   | house     | house |
        And all results contain
          | label |
          | 1019, Grosssteg, Sücka, Triesenberg, Oberland, 9497, Liechtenstein |
        And all results have no attributes name

    Scenario: Reverse geocodejson - Line geometry output is supported
        When sending v1/reverse with format geocodejson
          | lat      | lon     | polygon_geojson |
          | 47.06597 | 9.50467 | 1  |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
          | geojson+type |
          | LineString   |

    Scenario Outline: Reverse geocodejson - Only geojson polygons are supported
        When sending v1/reverse with format geocodejson
          | lat      | lon     | <param> |
          | 47.06597 | 9.50467 | 1       |
        Then a HTTP 200 is returned
        And the result is valid geocodejson with 1 result
        And all results contain
          | geojson+type |
          | Point        |

        Examples:
          | param |
          | polygon_text |
          | polygon_svg  |
          | polygon_kml  |

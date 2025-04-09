Feature: Geometries for reverse geocoding
    Tests for returning geometries with reverse

    Scenario: Reverse - polygons are returned fully by default
        When sending v1/reverse
          | lat      | lon     | polygon_text |
          | 47.13803 | 9.52264 | 1            |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | geotext!fm |
          | POLYGON\(\(9.5225302 47.138066, ?9.5225348 47.1379282, ?9.5226142 47.1379294, ?9.5226143 47.1379257, ?9.522615 47.137917, ?9.5226225 47.1379098, ?9.5226334 47.1379052, ?9.5226461 47.1379037, ?9.5226588 47.1379056, ?9.5226693 47.1379107, ?9.5226762 47.1379181, ?9.5226762 47.1379268, ?9.5226761 47.1379308, ?9.5227366 47.1379317, ?9.5227352 47.1379753, ?9.5227608 47.1379757, ?9.5227595 47.1380148, ?9.5227355 47.1380145, ?9.5227337 47.1380692, ?9.5225302 47.138066\)\) |


    Scenario: Reverse - polygons can be slightly simplified
        When sending v1/reverse
          | lat      | lon     | polygon_text | polygon_threshold |
          | 47.13803 | 9.52264 | 1            | 0.00001            |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | geotext!fm |
          | POLYGON\(\(9.5225302 47.138066, ?9.5225348 47.1379282, ?9.5226142 47.1379294, ?9.5226225 47.1379098, ?9.5226588 47.1379056, ?9.5226761 47.1379308, ?9.5227366 47.1379317, ?9.5227352 47.1379753, ?9.5227608 47.1379757, ?9.5227595 47.1380148, ?9.5227355 47.1380145, ?9.5227337 47.1380692, ?9.5225302 47.138066\)\) |


    Scenario: Reverse - polygons can be much simplified
        When sending v1/reverse
          | lat      | lon     | polygon_text | polygon_threshold |
          | 47.13803 | 9.52264 | 1            | 0.9               |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | geotext!fm |
          | POLYGON\(\([0-9. ]+, ?[0-9. ]+, ?[0-9. ]+, ?[0-9. ]+(, ?[0-9. ]+)?\)\) |


    Scenario: Reverse - for polygons return the centroid as center point
        When sending v1/reverse
          | lat      | lon     |
          | 47.13836 | 9.52304 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | lon       | lat        |
          | 9.5227108 | 47.1381805 |


    Scenario: Reverse - for streets return the closest point as center point
        When sending v1/reverse
          | lat      | lon     |
          | 47.13368 | 9.52942 |
        Then a HTTP 200 is returned
        And the result is valid xml
        And the result contains
          | lon       | lat        |
          | 9.5294315 | 47.1336817 |

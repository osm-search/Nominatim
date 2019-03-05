@APIDB
Feature: Parameters for Reverse API
    Testing different parameter options for reverse API.

    Scenario Outline: Reverse-geocoding without address
        When sending <format> reverse coordinates 53.603,10.041
          | addressdetails |
          | 0 |
        Then exactly 1 result is returned
        And result has not attributes address

    Examples:
      | format |
      | json |
      | jsonv2 |
      | geojson |
      | xml |

    Scenario Outline: Coordinates must be floating-point numbers
        When sending reverse coordinates <coords>
        Then a HTTP 400 is returned

    Examples:
      | coords    |
      | -45.3,;   |
      | gkjd,50   |

    Scenario Outline: Reverse Geocoding with extratags
        When sending <format> reverse coordinates 10.776234290950017,106.70425325632095
          | extratags |
          | 1 |
        Then result 0 has attributes extratags

    Examples:
        | format |
        | xml |
        | json |
        | jsonv2 |
        | geojson |

    Scenario Outline: Reverse Geocoding with namedetails
        When sending <format> reverse coordinates 10.776455623137625,106.70175343751907
          | namedetails |
          | 1 |
        Then result 0 has attributes namedetails

    Examples:
        | format |
        | xml |
        | json |
        | jsonv2 |
        | geojson |

    Scenario Outline: Reverse Geocoding contains TEXT geometry
        When sending <format> reverse coordinates 47.165989816710066,9.515774846076965
          | polygon_text |
          | 1 |
        Then result 0 has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geotext |
        | json     | geotext |
        | jsonv2   | geotext |

    Scenario Outline: Reverse Geocoding contains SVG geometry
        When sending <format> reverse coordinates 47.165989816710066,9.515774846076965
          | polygon_svg |
          | 1 |
        Then result 0 has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geosvg |
        | json     | svg |
        | jsonv2   | svg |

    Scenario Outline: Reverse Geocoding contains KML geometry
        When sending <format> reverse coordinates 47.165989816710066,9.515774846076965
          | polygon_kml |
          | 1 |
        Then result 0 has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geokml |
        | json     | geokml |
        | jsonv2   | geokml |

    Scenario Outline: Reverse Geocoding contains GEOJSON geometry
        When sending <format> reverse coordinates 47.165989816710066,9.515774846076965
          | polygon_geojson |
          | 1 |
        Then result 0 has attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | geojson |
        | json     | geojson |
        | jsonv2   | geojson |
        | geojson  | geojson |

    Scenario Outline: Reverse Geocoding in geojson format contains no non-geojson geometry
        When sending geojson reverse coordinates 47.165989816710066,9.515774846076965
          | polygon_text | polygon_svg | polygon_geokml |
          | 1            | 1           | 1              |
        Then result 0 has not attributes <response_attribute>

    Examples:
        | response_attribute |
        | geotext            |
        | polygonpoints      |
        | svg                |
        | geokml             |

    Scenario Outline: Reverse Geocoding with old deprecated polygon type
        When sending <format> reverse coordinates 47.165989816710066,9.515774846076965
          | polygon |
          | 1       |
        Then a HTTP 400 is returned

    Examples:
        | format   |
        | xml      |
        | json     |
        | jsonv2   |
        | geojson  |

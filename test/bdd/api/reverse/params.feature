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
      | xml |

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

    Scenario Outline: Reverse Geocoding contains polygon-as-points geometry
        When sending <format> reverse coordinates 47.165989816710066,9.515774846076965
          | polygon |
          | 1 |
        Then result 0 has not attributes <response_attribute>

    Examples:
        | format   | response_attribute |
        | xml      | polygonpoints |
        | json     | polygonpoints |
        | jsonv2   | polygonpoints |

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



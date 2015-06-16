Feature: Reverse lookup by ID
    Testing reverse geocoding via OSM ID

    # see github issue #269
    Scenario: Get address of linked places
        Given the request parameters
          | osm_type | osm_id
          | N        | 151421301
        When sending an API call reverse
        Then exactly 1 result is returned
        And result addresses contain
          | county       | state
          | Pratt County | Kansas

Feature: Places by osm_type and osm_id Tests
    Simple tests for internal server errors and response format.

    Scenario: address lookup for existing node, way, relation
        When looking up xml places N158845944,W72493656,,R62422,X99,N0
        Then the result is valid xml
        exactly 3 results are returned
        When looking up json places N158845944,W72493656,,R62422,X99,N0
        Then the result is valid json
        exactly 3 results are returned

    Scenario: address lookup for non-existing or invalid node, way, relation
        When looking up xml places X99,,N0,nN158845944,ABC,,W9
        Then the result is valid xml
        exactly 0 results are returned
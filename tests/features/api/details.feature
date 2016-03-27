Feature: Object details
    Check details page for correctness

    Scenario Outline: Details via OSM id
        When looking up details for <object>
        Then the result is valid

    Examples:
     | object
     | 1758375
     | N158845944
     | W72493656
     | R62422

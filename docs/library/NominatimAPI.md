# The Nominatim API classes

The API classes are the core object of the search library. Always instantiate
one of these classes first. The API classes are **not threadsafe**. You need
to instantiate a separate instance for each thread.

### NominatimAPI

::: nominatim.api.NominatimAPI
    options:
        members:
            - __init__
            - config
            - close
            - status
            - details
            - lookup
            - reverse
            - search
            - search_address
            - search_category
        heading_level: 6
        group_by_category: False
        show_signature_annotations: True


### NominatimAPIAsync

::: nominatim.api.NominatimAPIAsync
    options:
        members:
            - __init__
            - setup_database
            - close
            - begin
        heading_level: 6
        group_by_category: False
        show_signature_annotations: True

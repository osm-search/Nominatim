# Input Parameter Types

This page describes in more detail some of the input parameter types used
in the query functions of the API object.

## Place identification

The [details](NominatimAPI.md#nominatim_api.NominatimAPI.details) and
[lookup](NominatimAPI.md#nominatim_api.NominatimAPI.lookup) functions
require references to places in the database. Below the possible
types for place identification are listed. All types are dataclasses.

### PlaceID

::: nominatim_api.PlaceID
    options:
        heading_level: 6

### OsmID

::: nominatim_api.OsmID
    options:
        heading_level: 6

## Geometry types

::: nominatim_api.GeometryFormat
    options:
        heading_level: 6
        members_order: source

## Geometry input

### Point

::: nominatim_api.Point
    options:
        heading_level: 6
        show_signature_annotations: True

### Bbox

::: nominatim_api.Bbox
    options:
        heading_level: 6
        show_signature_annotations: True
        members_order: source
        group_by_category: False

## Layers

Layers allow to restrict the search result to thematic groups. This is
orthogonal to restriction by address ranks, which groups places by their
geographic extent.


::: nominatim_api.DataLayer
    options:
        heading_level: 6
        members_order: source

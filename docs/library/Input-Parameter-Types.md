# Input Parameter Types

This page describes in more detail some of the input parameter types used
in the query functions of the API object.

## Place identification

The [details](NominatimAPI.md#nominatim.api.core.NominatimAPI.details) and
[lookup](NominatimAPI.md#nominatim.api.core.NominatimAPI.lookup) functions
require references to places in the database. Below are listed the possible
types for place identification. All types are dataclasses.

### PlaceID

::: nominatim.api.PlaceID
    options:
        heading_level: 6

### OsmID

::: nominatim.api.OsmID
    options:
        heading_level: 6

## Geometry types

::: nominatim.api.GeometryFormat
    options:
        heading_level: 6
        members_order: source

## Geometry input

### Point

::: nominatim.api.Point
    options:
        heading_level: 6
        show_signature_annotations: True

### Bbox

::: nominatim.api.Bbox
    options:
        heading_level: 6
        show_signature_annotations: True
        members_order: source
        group_by_category: False

## Layers

::: nominatim.api.DataLayer
    options:
        heading_level: 6



# Result handling

The search functions of the Nominatim API always return a result object that
contains the full raw information about the place that is available in the
database. This section discusses data types used in the results and utility
functions that allow further processing of the results.

## Result fields

### Sources

Nominatim takes the result data from multiple souces. The `source_table` field
in the result describes, from which source the result was retrived.

::: nominatim.api.SourceTable
    options:
        heading_level: 6
        members_order: source

### Detailed address description

When the `address_details` parameter is set, then functions return not
only information about the result place but also about the place that
make up the address. This information is almost always required, when you
want to present the user with a human-readable description of the result.
See also [Localization](#localization) below.

The address details are available in the `address_rows` field as a ordered
list of `AddressLine` objects with the country information last. The list also
contains the result place itself and some artificial entries, for example,
for the housenumber or the country code. This makes processing and creating
a full address easiert.

::: nominatim.api.AddressLine
    options:
        heading_level: 6
        members_order: source

### Detailed search terms

The `details` function can return detailed information about which search terms
may be used to find a place, when the `keywords` parameter is set. Search
terms are split into terms for the name of the place and search terms for
its address.

::: nominatim.api.WordInfo
    options:
        heading_level: 6

## Localization

Results are always returned with the full list of available names.

### Locale

::: nominatim.api.Locales
    options:
        heading_level: 6

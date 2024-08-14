# Changing the Appearance of Results in the Server API

The Nominatim Server API offers a number of formatting options that
present search results in [different output formats](../api/Output.md).
These results only contain a subset of all the information that Nominatim
has about the result. This page explains how to adapt the result output
or add additional result formatting.

## Defining custom result formatting

To change the result output, you need to place a file `api/v1/format.py`
into your project directory. This file needs to define a single variable
`dispatch` containing a [FormatDispatcher](#formatdispatcher). This class
serves to collect the functions for formatting the different result types
and offers helper functions to apply the formatters.

There are two ways to define the `dispatch` variable. If you want to reuse
the default output formatting and just make some changes or add an additional
format type, then import the dispatch object from the default API:

``` python
from nominatim_api.v1.format import dispatch as dispatch
```

If you prefer to define a completely new result output, then you can
create an empty dispatcher object:

``` python
from nominatim_api import FormatDispatcher

dispatch = FormatDispatcher()
```

## The formatting function

The dispatcher organises the formatting functions by format and result type.
The format corresponds to the `format` parameter of the API. It can contain
one of the predefined format names or you can invent your own new format.

API calls return data classes or an array of a data class which represent
the result. You need to make sure there are formatters defined for the
following result types:

* StatusResult (single object, returned by `/status`)
* DetailedResult (single object, returned by `/details`)
* SearchResults (list of objects, returned by `/search`)
* ReverseResults (list of objects, returned by `/reverse` and `/lookup`)
* RawDataList (simple object, returned by `/deletable` and `/polygons`)

A formatter function has the following signature:

``` python
def format_func(result: ResultType, options: Mapping[str, Any]) -> str
```

The options dictionary contains additional information about the original
query. See the [reference below](#options-for-different-result-types)
about the possible options.

To set the result formatter for a certain result type and format, you need
to write the format function and decorate it with the
[`format_func`](#nominatim_api.FormatDispatcher.format_func)
decorator.

For example, let us extend the result for the status call in text format
and add the server URL. Such a formatter would look like this:

``` python
@dispatch.format_func(StatusResult, 'text')
def _format_status_text(result, _):
    header = 'Status for server nominatim.openstreetmap.org'
    if result.status:
        return f"{header}\n\nERROR: {result.message}"

    return f"{header}\n\nOK"
```

If your dispatcher is derived from the default one, then this definition
will overwrite the original formatter function. This way it is possible
to customize the output of selected results.

## Adding new formats

You may also define a completely different output format. This is as simple
as adding formatting functions for all result types using the custom
format name:

``` python
@dispatch.format_func(StatusResult, 'chatty')
def _format_status_text(result, _):
    if result.status:
        return f"The server is currently not running. {result.message}"

    return f"Good news! The server is running just fine."
```

That's all. Nominatim will automatically pick up the new format name and
will allow the user to use it. Make sure to really define formatters for
**all** result types. If they are for endpoints that you do not intend to
use, you can simply return some static string but the function needs to be
there.

All responses will be returned with the content type application/json by
default. If your format produces a different content type, you need
to configure the content type with the `set_content_type()` function.

For example, the 'chatty' format above returns just simple text. So the
content type should be set up as:

``` python
from nominatim_api.server.content_types import CONTENT_TEXT

dispatch.set_content_type('chatty', CONTENT_TEXT)
```

The `content_types` module used above provides constants for the most
frequent content types. You set the content type to an arbitrary string,
if the content type you need is not available.

## Reference

### FormatDispatcher

::: nominatim_api.FormatDispatcher
    options:
        heading_level: 6
        group_by_category: False

### JsonWriter

::: nominatim_api.utils.json_writer.JsonWriter
    options:
        heading_level: 6
        group_by_category: False

### Options for different result types

This section lists the options that may be handed in with the different result
types in the v1 version of the Nominatim API.

#### StatusResult

_None._

#### DetailedResult

| Option          | Description |
|-----------------|-------------|
| locales         | [Locale](../library/Result-Handling.md#locale) object for the requested language(s) |
| group_hierarchy | Setting of [group_hierarchy](../api/Details.md#output-details) parameter |
| icon_base_url   | (optional) URL pointing to icons as set in [NOMINATIM_MAPICON_URL](Settings.md#nominatim_mapicon_url) |

#### SearchResults

| Option          | Description |
|-----------------|-------------|
| query           | Original query string |
| more_url        | URL for requesting additional results for the same query |
| exclude_place_ids | List of place IDs already returned |
| viewbox         | Setting of [viewbox](../api/Search.md#result-restriction) parameter |
| extratags       | Setting of [extratags](../api/Search.md#output-details) parameter |
| namedetails     | Setting of [namedetails](../api/Search.md#output-details) parameter |
| addressdetails  | Setting of [addressdetails](../api/Search.md#output-details) parameter |

#### ReverseResults

| Option          | Description |
|-----------------|-------------|
| query           | Original query string |
| extratags       | Setting of [extratags](../api/Search.md#output-details) parameter |
| namedetails     | Setting of [namedetails](../api/Search.md#output-details) parameter |
| addressdetails  | Setting of [addressdetails](../api/Search.md#output-details) parameter |

#### RawDataList

_None._

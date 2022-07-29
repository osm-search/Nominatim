# Writing custom sanitizer and token analysis modules for the ICU tokenizer

The [ICU tokenizer](../customize/Tokenizers.md#icu-tokenizer) provides a
highly customizable method to pre-process and normalize the name information
of the input data before it is added to the search index. It comes with a
selection of sanitizers and token analyzers which you can use to adapt your
installation to your needs. If the provided modules are not enough, you can
also provide your own implementations. This section describes how to do that.

!!! warning
    This API is currently in early alpha status. While this API is meant to
    be a public API on which other sanitizers and token analyzers may be
    implemented, it is not guaranteed to be stable at the moment.


## Using non-standard sanitizers and token analyzers

Sanitizer names (in the `step` property) and token analysis names (in the
`analyzer`) may refer to externally supplied modules. There are two ways
to include external modules: through a library or from the project directory.

To include a module from a library, use the absolute import path as name and
make sure the library can be found in your PYTHONPATH.

To use a custom module without creating a library, you can put the module
somewhere in your project directory and then use the relative path to the
file. Include the whole name of the file including the `.py` ending.

## Custom sanitizer modules

A sanitizer module must export a single factory function `create` with the
following signature:

``` python
def create(config: SanitizerConfig) -> Callable[[ProcessInfo], None]
```

The function receives the custom configuration for the sanitizer and must
return a callable (function or class) that transforms the name and address
terms of a place. When a place is processed, then a `ProcessInfo` object
is created from the information that was queried from the database. This
object is sequentially handed to each configured sanitizer, so that each
sanitizer receives the result of processing from the previous sanitizer.
After the last sanitizer is finished, the resulting name and address lists
are forwarded to the token analysis module.

Sanitizer functions are instantiated once and then called for each place
that is imported or updated. They don't need to be thread-safe.
If multi-threading is used, each thread creates their own instance of
the function.

### Sanitizer configuration

::: nominatim.tokenizer.sanitizers.config.SanitizerConfig
    rendering:
        show_source: no
        heading_level: 6

### The sanitation function

The sanitation function receives a single object of type `ProcessInfo`
which has with three members:

 * `place`: read-only information about the place being processed.
   See PlaceInfo below.
 * `names`: The current list of names for the place. Each name is a
   PlaceName object.
 * `address`: The current list of address names for the place. Each name
   is a PlaceName object.

While the `place` member is provided for information only, the `names` and
`address` lists are meant to be manipulated by the sanitizer. It may add and
remove entries, change information within a single entry (for example by
adding extra attributes) or completely replace the list with a different one.

#### PlaceInfo - information about the place

::: nominatim.data.place_info.PlaceInfo
    rendering:
        show_source: no
        heading_level: 6


#### PlaceName - extended naming information

::: nominatim.data.place_name.PlaceName
    rendering:
        show_source: no
        heading_level: 6

## Custom token analysis module

Setup of a token analyser is split into two parts: configuration and
analyser factory. A token analysis module must therefore implement two
functions:

::: nominatim.tokenizer.token_analysis.base.AnalysisModule
    rendering:
        show_source: no
        heading_level: 6


::: nominatim.tokenizer.token_analysis.base.Analyzer
    rendering:
        show_source: no
        heading_level: 6

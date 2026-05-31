# Writing custom sanitizer modules

Sanitizers are used for preprocessing name and address information
from the OpenStreetMap input data for the search index. Read more about
them in the [Customizing sanitizers](../customize/Sanitizers.md) section.

This section explains how to write your own sanitizer step function.

## Using custom sanitizer modules

To use a custom made sanitizer step, simply refer to the sanitizer module
in the `step` property. There are two ways
to include external modules: through a library or from the project directory.

To include a module from a library, use the absolute import path as name and
make sure the library can be found in your PYTHONPATH.

!!! Example
    You have your sanitizer steps in a Python package my_sanitizer and
    want to refer to the step implemented in module `translate_street.py`.

    ```
    - step: my_sanitizer.translate_street
      config: some other config info for the step
    ```

To use a custom module without creating a library, you can put the module
somewhere in your project directory and then use the relative path to the
file. Include the whole name of the file including the `.py` ending.

!!! Example
    You have put your module `translate_street.py` directly into the project
    directory.

    ```
    - step: translate_street.py
      config: some other config info for the step
    ```

## Basic sanitizer module setup

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

::: nominatim_db.tokenizer.sanitizers.config.SanitizerConfig
    options:
        heading_level: 6

### The main filter function of the sanitizer

The filter function receives a single object of type `ProcessInfo`
which has with three members:

 * `place: PlaceInfo`: read-only information about the place being processed.
   See PlaceInfo below.
 * `names: List[PlaceName]`: The current list of names for the place.
 * `address: List[PlaceName]`: The current list of address names for the place.

While the `place` member is provided for information only, the `names` and
`address` lists are meant to be manipulated by the sanitizer. It may add and
remove entries, change information within a single entry (for example by
adding extra attributes) or completely replace the list with a different one.

#### PlaceInfo - information about the place

::: nominatim_db.data.place_info.PlaceInfo
    options:
        heading_level: 6


#### PlaceName - extended naming information

::: nominatim_db.data.place_name.PlaceName
    options:
        heading_level: 6


### Example: Filter for US street prefixes

The following sanitizer removes the directional prefixes from street names
in the US:

!!! example
    ``` python
    import re

    def _filter_function(obj):
        if obj.place.country_code == 'us' \
           and obj.place.rank_address >= 26 and obj.place.rank_address <= 27:
            for name in obj.names:
                name.name = re.sub(r'^(north|south|west|east) ',
                                   '',
                                   name.name,
                                   flags=re.IGNORECASE)

    def create(config):
        return _filter_function
    ```

This is the most simple form of a sanitizer module. If defines a single
filter function and implements the required `create()` function by returning
the filter.

The filter function first checks if the object is interesting for the
sanitizer. Namely it checks if the place is in the US (through `country_code`)
and it the place is a street (a `rank_address` of 26 or 27). If the
conditions are met, then it goes through all available names and
removes any leading directional prefix using a simple regular expression.

Save the source code in a file in your project directory, for example as
`us_streets.py`. Then you can use the sanitizer in your `icu_tokenizer.yaml`:

``` yaml
...
sanitizers:
    - step: us_streets.py
...
```

!!! warning
    This example is just a simplified show case on how to create a sanitizer.
    It is not really meant for real-world use: while the sanitizer would
    correctly transform `West 5th Street` into `5th Street`. it would also
    shorten a simple `North Street` to `Street`.

For more sanitizer examples, have a look at the sanitizers provided by Nominatim.
They can be found in the directory
[`src/nominatim_db/tokenizer/sanitizers`](https://github.com/osm-search/Nominatim/tree/master/src/nominatim_db/tokenizer/sanitizers).





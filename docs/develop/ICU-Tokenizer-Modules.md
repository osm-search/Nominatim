# Writing custom sanitizer and token analysis modules for the ICU tokenizer

The [ICU tokenizer](../customize/Tokenizers.md#icu-tokenizer) provides a
highly customizable method to pre-process and normalize the name information
of the input data before it is added to the search index. It comes with a
selection of sanitizers and token analyzers which you can use to adapt your
installation to your needs. If the provided modules are not enough, you can
also provide your own implementations. This section describes the API
of sanitizers and token analysis.

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

### The main filter function of the sanitizer

The filter function receives a single object of type `ProcessInfo`
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


### Example: Filter for US street prefixes

The following sanitizer removes the directional prefixes from street names
in the US:

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
    It is not really read for real-world use: while the sanitizer would
    correcly transform `West 5th Street` into `5th Street`. it would also
    shorten a simple `North Street` to `Street`.

For more sanitizer examples, have a look at the sanitizers provided by Nominatim.
They can be found in the directory
[`nominatim/tokenizer/sanitizers`](https://github.com/osm-search/Nominatim/tree/master/nominatim/tokenizer/sanitizers).


## Custom token analysis module

::: nominatim.tokenizer.token_analysis.base.AnalysisModule
    rendering:
        show_source: no
        heading_level: 6


::: nominatim.tokenizer.token_analysis.base.Analyzer
    rendering:
        show_source: no
        heading_level: 6

### Example: Creating acronym variants for long names

The following example of a token analysis module creates acronyms from
very long names and adds them as a variant:

``` python
class AcronymMaker:
    """ This class is the actual analyzer.
    """
    def __init__(self, norm, trans):
        self.norm = norm
        self.trans = trans


    def get_canonical_id(self, name):
        # In simple cases, the normalized name can be used as a canonical id.
        return self.norm.transliterate(name.name).strip()


    def compute_variants(self, name):
        # The transliterated form of the name always makes up a variant.
        variants = [self.trans.transliterate(name)]

        # Only create acronyms from very long words.
        if len(name) > 20:
            # Take the first letter from each word to form the acronym.
            acronym = ''.join(w[0] for w in name.split())
            # If that leds to an acronym with at least three letters,
            # add the resulting acronym as a variant.
            if len(acronym) > 2:
                # Never forget to transliterate the variants before returning them.
                variants.append(self.trans.transliterate(acronym))

        return variants

# The following two functions are the module interface.

def configure(rules, normalizer, transliterator):
    # There is no configuration to parse and no data to set up.
    # Just return an empty configuration.
    return None


def create(normalizer, transliterator, config):
    # Return a new instance of our token analysis class above.
    return AcronymMaker(normalizer, transliterator)
```

Given the name `Trans-Siberian Railway`, the code above would return the full
name `Trans-Siberian Railway` and the acronym `TSR` as variant, so that
searching would work for both.

## Sanitizers vs. Token analysis - what to use for variants?

It is not always clear when to implement variations in the sanitizer and
when to write a token analysis module. Just take the acronym example
above: it would also have been possible to write a sanitizer which adds the
acronym as an additional name to the name list. The result would have been
similar. So which should be used when?

The most important thing to keep in mind is that variants created by the
token analysis are only saved in the word lookup table. They do not need
extra space in the search index. If there are many spelling variations, this
can mean quite a significant amount of space is saved.

When creating additional names with a sanitizer, these names are completely
independent. In particular, they can be fed into different token analysis
modules. This gives a much greater flexibility but at the price that the
additional names increase the size of the search index.


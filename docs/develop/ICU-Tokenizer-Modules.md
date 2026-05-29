# Writing custom token analysis modules for the ICU tokenizer

The [ICU tokenizer](../customize/Tokenizers.md#icu-tokenizer) provides a
highly customizable method to pre-process and normalize the name information
of the input data before it is added to the search index. It comes with a
selection of token analyzers which you can use to adapt your
installation to your needs. If the provided modules are not enough, you can
also provide your own implementations. This section describes the API
for token analysis.

!!! warning
    This API is currently in early alpha status. While this API is meant to
    be a public API on which other token analyzers may be
    implemented, it is not guaranteed to be stable at the moment.


## Using non-standard modules

Token analysis names (in the
`analyzer`) and query preprocessor names (in the `step` property)
may refer to externally supplied modules. There are two ways
to include external modules: through a library or from the project directory.

To include a module from a library, use the absolute import path as name and
make sure the library can be found in your PYTHONPATH.

To use a custom module without creating a library, you can put the module
somewhere in your project directory and then use the relative path to the
file. Include the whole name of the file including the `.py` ending.

## Custom query preprocessors

A query preprocessor must export a single factory function `create` with
the following signature:

``` python
create(self, config: QueryConfig) -> Callable[[list[Phrase]], list[Phrase]]
```

The function receives the custom configuration for the preprocessor and
returns a callable (function or class) with the actual preprocessing
code. When a query comes in, then the callable gets a list of phrases
and needs to return the transformed list of phrases. The list and phrases
may be changed in place or a completely new list may be generated.

The `QueryConfig` is a simple dictionary which contains all configuration
options given in the yaml configuration of the ICU tokenizer. It is up to
the function to interpret the values.

A `nominatim_api.search.Phrase` describes a part of the query that contains one or more independent
search terms. Breaking a query into phrases helps reducing the number of
possible tokens Nominatim has to take into account. However a phrase break
is definitive: a multi-term search word cannot go over a phrase break.
A Phrase object has two fields:

 * `ptype` further refines the type of phrase (see list below)
 * `text` contains the query text for the phrase

The order of phrases matters to Nominatim when doing further processing.
Thus, while you may split or join phrases, you should not reorder them
unless you really know what you are doing.

Phrase types can further help narrowing down how the tokens in the phrase
are interpreted. The following phrase types are known:

| Name           | Description |
|----------------|-------------|
| PHRASE_ANY     | No specific designation (i.e. source is free-form query) |
| PHRASE_AMENITY | Contains name or type of a POI |
| PHRASE_STREET  | Contains a street name optionally with a housenumber |
| PHRASE_CITY    | Contains the postal city |
| PHRASE_COUNTY  | Contains the equivalent of a county |
| PHRASE_STATE   | Contains a state or province |
| PHRASE_POSTCODE| Contains a postal code |
| PHRASE_COUNTRY | Contains the country name or code |


## Custom token analysis module

::: nominatim_db.tokenizer.token_analysis.base.AnalysisModule
    options:
        heading_level: 6


::: nominatim_db.tokenizer.token_analysis.base.Analyzer
    options:
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


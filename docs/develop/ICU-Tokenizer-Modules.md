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


## Using custom token analysis modules

Token analysis names as set in the `analyzer` property
may refer to externally supplied modules. There are two ways
to include external modules: through a library or from the project directory.

To include a module from a library, use the absolute import path as name and
make sure the library can be found in your PYTHONPATH.

To use a custom module without creating a library, you can put the module
somewhere in your project directory and then use the relative path to the
file. Include the whole name of the file including the `.py` ending.


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


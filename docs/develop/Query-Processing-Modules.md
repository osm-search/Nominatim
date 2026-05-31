# Writing custom query processing modules

Query processing allows to transform incoming queries before handing them
to the search engine. Read more about them in the
[Query Preprocessing](../customize/Query-Preprocessing.md) section.

## Using custom preprocessing modules
 
To use a custom made preprocessing step, simply refer to the preprocessing module
in the `step` property. There are two ways
to include external modules: through a library or from the project directory.

To include a module from a library, use the absolute import path as name and
make sure the library can be found in your PYTHONPATH.

!!! Example
    You have your preprocesser steps in a Python package my_modules and
    want to refer to the step implemented in module `delete_ip_addresses.py`.

    ```
    - step: my_modules.delete_ip_addresses
      config: some other config info for the step
    ```

To use a custom module without creating a library, you can put the module
somewhere in your project directory and then use the relative path to the
file. Include the whole name of the file including the `.py` ending.

!!! Example
    You have put your module `delete_ip_addresses.py` directly into the project
    directory.

    ```
    - step: delete_ip_addresses.py
      config: some other config info for the step
    ```

## Basic sanitizer module setup

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


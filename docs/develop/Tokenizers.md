# Tokenizers

The tokenizer is the component of Nominatim that is responsible for
analysing names of OSM objects and queries. Nominatim provides different
tokenizers that use different strategies for normalisation. This page describes
how tokenizers are expected to work and the public API that needs to be
implemented when creating a new tokenizer. For information on how to configure
a specific tokenizer for a database see the
[tokenizer chapter in the administration guide](../admin/Tokenizers.md).

## Generic Architecture

### About Search Tokens

Search in Nominatim is organised around search tokens. Such a token represents
string that can be part of the search query. Tokens are used so that the search
index does not need to be organised around strings. Instead the database saves
for each place which tokens match this place's name, address, house number etc.
To be able to distinguish between these different types of information stored
with the place, a search token also always has a certain type: name, house number,
postcode etc.

During search an incoming query is transformed into a ordered list of such
search tokens (or rather many lists, see below) and this list is then converted
into a database query to find the right place.

It is the core task of the tokenizer to create, manage and assign the search
tokens. The tokenizer is involved in two distinct operations:

* __at import time__: scanning names of OSM objects, normalizing them and
  building up the list of search tokens.
* __at query time__: scanning the query and returning the appropriate search
  tokens.


### Importing

The indexer is responsible to enrich an OSM object (or place) with all data
required for geocoding. It is split into two parts: the controller collects
the places that require updating, enriches the place information as required
and hands the place to Postgresql. The collector is part of the Nominatim
library written in Python. Within Postgresql, the `placex_update`
trigger is responsible to fill out all secondary tables with extra geocoding
information. This part is written in PL/pgSQL.

The tokenizer is involved in both parts. When the indexer prepares a place,
it hands it over to the tokenizer to inspect the names and create all the
search tokens applicable for the place. This usually involves updating the
tokenizer's internal token lists and creating a list of all token IDs for
the specific place. This list is later needed in the PL/pgSQL part where the
indexer needs to add the token IDs to the appropriate search tables. To be
able to communicate the list between the Python part and the pl/pgSQL trigger,
the placex table contains a special JSONB column `token_info` which is there
for the exclusive use of the tokenizer.

The Python part of the tokenizer returns a structured information about the
tokens of a place to the indexer which converts it to JSON and inserts it into
the `token_info` column. The content of the column is then handed to the PL/pqSQL
callbacks of the tokenizer which extracts the required information. Usually
the tokenizer then removes all information from the `token_info` structure,
so that no information is ever persistently saved in the table. All information
that went in should have been processed after all and put into secondary tables.
This is however not a hard requirement. If the tokenizer needs to store
additional information about a place permanently, it may do so in the
`token_info` column. It just may never execute searches over it and
consequently not create any special indexes on it.

### Querying

The tokenizer is responsible for the initial parsing of the query. It needs
to split the query into appropriate words and terms and match them against
the saved tokens in the database. It then returns the list of possibly matching
tokens and the list of possible splits to the query parser. The parser uses
this information to compute all possible interpretations of the query and
rank them accordingly.

## Tokenizer API

The following section describes the functions that need to be implemented
for a custom tokenizer implementation.

!!! warning
    This API is currently in early alpha status. While this API is meant to
    be a public API on which other tokenizers may be implemented, the API is
    far away from being stable at the moment.

### Directory Structure

Nominatim expects two files for a tokenizer:

* `nominiatim/tokenizer/<NAME>_tokenizer.py` containing the Python part of the
  implementation
* `lib-php/tokenizer/<NAME>_tokenizer.php` with the PHP part of the
  implementation

where `<NAME>` is a unique name for the tokenizer consisting of only lower-case
letters, digits and underscore. A tokenizer also needs to install some SQL
functions. By convention, these should be placed in `lib-sql/tokenizer`.

If the tokenizer has a default configuration file, this should be saved in
the `settings/<NAME>_tokenizer.<SUFFIX>`.

### Configuration and Persistance

Tokenizers may define custom settings for their configuration. All settings
must be prefixed with `NOMINATIM_TOKENIZER_`. Settings may be transient or
persistent. Transient settings are loaded from the configuration file when
Nominatim is started and may thus be changed at any time. Persistent settings
are tied to a database installation and must only be read during installation
time. If they are needed for the runtime then they must be saved into the
`nominatim_properties` table and later loaded from there.

### The Python module

The Python module is expect to export a single factory function:

```python
def create(dsn: str, data_dir: Path) -> AbstractTokenizer
```

The `dsn` parameter contains the DSN of the Nominatim database. The `data_dir`
is a directory in the project directory that the tokenizer may use to save
database-specific data. The function must return the instance of the tokenizer
class as defined below.

### Python Tokenizer Class

All tokenizers must inherit from `nominatim.tokenizer.base.AbstractTokenizer`
and implement the abstract functions defined there.

::: nominatim.tokenizer.base.AbstractTokenizer
    rendering:
        heading_level: 4

### Python Analyzer Class

::: nominatim.tokenizer.base.AbstractAnalyzer
    rendering:
        heading_level: 4

### PL/pgSQL Functions

The tokenizer must provide access functions for the `token_info` column
to the indexer which extracts the necessary information for the global
search tables. If the tokenizer needs additional SQL functions for private
use, then these functions must be prefixed with `token_` in order to ensure
that there are no naming conflicts with the SQL indexer code.

The following functions are expected:

```sql
FUNCTION token_get_name_search_tokens(info JSONB) RETURNS INTEGER[]
```

Return an array of token IDs of search terms that should match
the name(s) for the given place. These tokens are used to look up the place
by name and, where the place functions as part of an address for another place,
by address. Must return NULL when the place has no name.

```sql
FUNCTION token_get_name_match_tokens(info JSONB) RETURNS INTEGER[]
```

Return an array of token IDs of full names of the place that should be used
to match addresses. The list of match tokens is usually more strict than
search tokens as it is used to find a match between two OSM tag values which
are expected to contain matching full names. Partial terms should not be
used for match tokens. Must return NULL when the place has no name.

```sql
FUNCTION token_get_housenumber_search_tokens(info JSONB) RETURNS INTEGER[]
```

Return an array of token IDs of house number tokens that apply to the place.
Note that a place may have multiple house numbers, for example when apartments
each have their own number. Must be NULL when the place has no house numbers.

```sql
FUNCTION token_normalized_housenumber(info JSONB) RETURNS TEXT
```

Return the house number(s) in the normalized form that can be matched against
a house number token text. If a place has multiple house numbers they must
be listed with a semicolon as delimiter. Must be NULL when the place has no
house numbers.

```sql
FUNCTION token_addr_street_match_tokens(info JSONB) RETURNS INTEGER[]
```

Return the match token IDs by which to search a matching street from the
`addr:street` tag. These IDs will be matched against the IDs supplied by
`token_get_name_match_tokens`. Must be NULL when the place has no `addr:street`
tag.

```sql
FUNCTION token_addr_place_match_tokens(info JSONB) RETURNS INTEGER[]
```

Return the match token IDs by which to search a matching place from the
`addr:place` tag. These IDs will be matched against the IDs supplied by
`token_get_name_match_tokens`. Must be NULL when the place has no `addr:place`
tag.

```sql
FUNCTION token_addr_place_search_tokens(info JSONB) RETURNS INTEGER[]
```

Return the search token IDs extracted from the `addr:place` tag. These tokens
are used for searches by address when no matching place can be found in the
database. Must be NULL when the place has no `addr:place` tag.

```sql
CREATE TYPE token_addresstoken AS (
  key TEXT,
  match_tokens INT[],
  search_tokens INT[]
);

FUNCTION token_get_address_tokens(info JSONB) RETURNS SETOF token_addresstoken
```

Return the match and search token IDs for explicit `addr:*` tags for the place
other than `addr:street` and `addr:place`. For each address item there are
three pieces of information returned:

 * _key_ contains the type of address item (city, county, etc.). This is the
   key handed in with the `address` dictionary.
 * *match_tokens* is the list of token IDs used to find the corresponding
   place object for the address part. The list is matched against the IDs
   from `token_get_name_match_tokens`.
 * *search_tokens* is the list of token IDs under which to search the address
   item. It is used when no corresponding place object was found.

```sql
FUNCTION token_normalized_postcode(postcode TEXT) RETURNS TEXT
```

Return the normalized version of the given postcode. This function must return
the same value as the Python function `AbstractAnalyzer->normalize_postcode()`.

```sql
FUNCTION token_strip_info(info JSONB) RETURNS JSONB
```

Return the part of the `token_info` field that should be stored in the database
permanently. The indexer calls this function when all processing is done and
replaces the content of the `token_info` column with the returned value before
the trigger stores the information in the database. May return NULL if no
information should be stored permanently.

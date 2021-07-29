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



This section provides a reference of all configuration parameters that can
be used with Nominatim.

# Configuring Nominatim

Nominatim uses [dotenv](https://github.com/theskumar/python-dotenv) to manage
its configuration settings. There are two means to set configuration
variables: through an `.env` configuration file or through an environment
variable.

The `.env` configuration file needs to be placed into the
[project directory](../admin/Import.md#creating-the-project-directory). It
must contain configuration parameters in `<parameter>=<value>` format.
Please refer to the dotenv documentation for details.

The configuration options may also be set in the form of shell environment
variables. This is particularly useful, when you want to temporarily change
a configuration option. For example, to force the replication serve to
download the next change, you can temporarily disable the update interval:

    NOMINATIM_REPLICATION_UPDATE_INTERVAL=0 nominatim replication --once

If a configuration option is defined through .env file and environment
variable, then the latter takes precedence. 

## Configuration Parameter Reference

### Import and Database Settings

#### NOMINATIM_DATABASE_DSN

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Database connection string |
| **Format:**        | string: `pgsql:<param1>=<value1>;<param2>=<value2>;...` |
| **Default:**       | pgsql:dbname=nominatim |
| **After Changes:** | run `nominatim refresh --website` |

Sets the connection parameters for the Nominatim database. At a minimum
the name of the database (`dbname`) is required. You can set any additional
parameter that is understood by libpq. See the [Postgres documentation](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS) for a full list.

!!! note
    It is usually recommended not to set the password directly in this
    configuration parameter. Use a
    [password file](https://www.postgresql.org/docs/current/libpq-pgpass.html)
    instead.


#### NOMINATIM_DATABASE_WEBUSER

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Database query user |
| **Format:**        | string  |
| **Default:**       | www-data |
| **After Changes:** | cannot be changed after import |

Defines the name of the database user that will run search queries. Usually
this is the user under which the webserver is executed. When running Nominatim
via php-fpm, you can also define a separate query user. The Postgres user
needs to be set up before starting the import.

Nominatim grants minimal rights to this user to all tables that are needed
for running geocoding queries.


#### NOMINATIM_DATABASE_MODULE_PATH

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Directory where to find the PostgreSQL server module |
| **Format:**        | path |
| **Default:**       | _empty_ (use `<project_directory>/module`) |
| **After Changes:** | run `nominatim refresh --functions` |
| **Comment:**       | Legacy tokenizer only |

Defines the directory in which the PostgreSQL server module `nominatim.so`
is stored. The directory and module must be accessible by the PostgreSQL
server.

For information on how to use this setting when working with external databases,
see [Advanced Installations](../admin/Advanced-Installations.md).

The option is only used by the Legacy tokenizer and ignored otherwise.


#### NOMINATIM_TOKENIZER

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Tokenizer used for normalizing and parsing queries and names |
| **Format:**        | string |
| **Default:**       | legacy |
| **After Changes:** | cannot be changed after import |

Sets the tokenizer type to use for the import. For more information on
available tokenizers and how they are configured, see
[Tokenizers](../customize/Tokenizers.md).


#### NOMINATIM_TOKENIZER_CONFIG

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Configuration file for the tokenizer |
| **Format:**        | path |
| **Default:**       | _empty_ (default file depends on tokenizer) |
| **After Changes:** | see documentation for each tokenizer |

Points to the file with additional configuration for the tokenizer.
See the [Tokenizer](../customize/Tokenizers.md) descriptions for details
on the file format.

#### NOMINATIM_MAX_WORD_FREQUENCY

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Number of occurrences before a word is considered frequent |
| **Format:**        | int |
| **Default:**       | 50000 |
| **After Changes:** | cannot be changed after import |
| **Comment:**       | Legacy tokenizer only |

The word frequency count is used by the Legacy tokenizer to automatically
identify _stop words_. Any partial term that occurs more often then what
is defined in this setting, is effectively ignored during search.


#### NOMINATIM_LIMIT_REINDEXING

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Avoid invalidating large areas |
| **Format:**        | bool |
| **Default:**       | yes |

Nominatim computes the address of each place at indexing time. This has the
advantage to make search faster but also means that more objects needs to
be invalidated when the data changes. For example, changing the name of
the state of Florida would require recomputing every single address point
in the state to make the new name searchable in conjunction with addresses.

Setting this option to 'yes' means that Nominatim skips reindexing of contained
objects when the area becomes too large.


#### NOMINATIM_LANGUAGES

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Restrict search languages |
| **Format:**        | comma,separated list of language codes |
| **Default:**       | _empty_ |

Normally Nominatim will include all language variants of name:XX
in the search index. Set this to a comma separated list of language
codes, to restrict import to a subset of languages.

Currently only affects the initial import of country names and special phrases.


#### NOMINATIM_TERM_NORMALIZATION

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Rules for normalizing terms for comparisons |
| **Format:**        | string: semicolon-separated list of ICU rules |
| **Default:**       | :: NFD (); [[:Nonspacing Mark:] [:Cf:]] >;  :: lower (); [[:Punctuation:][:Space:]]+ > ' '; :: NFC (); |
| **Comment:**       | Legacy tokenizer only |

[Special phrases](Special-Phrases.md) have stricter matching requirements than
normal search terms. They must appear exactly in the query after this term
normalization has been applied.

Only has an effect on the Legacy tokenizer. For the ICU tokenizer the rules
defined in the
[normalization section](Tokenizers.md#normalization-and-transliteration)
will be used.


#### NOMINATIM_USE_US_TIGER_DATA

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Enable searching for Tiger house number data |
| **Format:**        | boolean |
| **Default:**       | no |
| **After Changes:** | run `nominatim --refresh --functions` |

When this setting is enabled, search and reverse queries also take data
from [Tiger house number data](Tiger.md) into account.


#### NOMINATIM_USE_AUX_LOCATION_DATA

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Enable searching in external house number tables |
| **Format:**        | boolean |
| **Default:**       | no |
| **After Changes:** | run `nominatim --refresh --functions` |
| **Comment:**       | Do not use. |

When this setting is enabled, search queries also take data from external
house number tables into account.

*Warning:* This feature is currently unmaintained and should not be used.


#### NOMINATIM_HTTP_PROXY

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Use HTTP proxy when downloading data |
| **Format:**        | boolean |
| **Default:**       | no |

When this setting is enabled and at least
[NOMINATIM_HTTP_PROXY_HOST](#nominatim_http_proxy_host) and
[NOMINATIM_HTTP_PROXY_PORT](#nominatim_http_proxy_port) are set, the
configured proxy will be used, when downloading external data like
replication diffs.


#### NOMINATIM_HTTP_PROXY_HOST

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Host name of the proxy to use |
| **Format:**        | string |
| **Default:**       | _empty_ |

When [NOMINATIM_HTTP_PROXY](#nominatim_http_proxy) is enabled, this setting
configures the proxy host name.


#### NOMINATIM_HTTP_PROXY_PORT

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Port number of the proxy to use |
| **Format:**        | integer |
| **Default:**       | 3128 |

When [NOMINATIM_HTTP_PROXY](#nominatim_http_proxy) is enabled, this setting
configures the port number to use with the proxy.


#### NOMINATIM_HTTP_PROXY_LOGIN

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Username for proxies that require login |
| **Format:**        | string |
| **Default:**       | _empty_ |

When [NOMINATIM_HTTP_PROXY](#nominatim_http_proxy) is enabled, use this
setting to define the username for proxies that require a login.


#### NOMINATIM_HTTP_PROXY_PASSWORD

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Password for proxies that require login |
| **Format:**        | string |
| **Default:**       | _empty_ |

When [NOMINATIM_HTTP_PROXY](#nominatim_http_proxy) is enabled, use this
setting to define the password for proxies that require a login.


#### NOMINATIM_OSM2PGSQL_BINARY

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Location of the osm2pgsql binary |
| **Format:**        | path |
| **Default:**       | _empty_ (use binary shipped with Nominatim) |
| **Comment:**       | EXPERT ONLY |

Nominatim uses [osm2pgsql](https://osm2pgsql.org) to load the OSM data
initially into the database. Nominatim comes bundled with a version of
osm2pgsql that is guaranteed to be compatible. Use this setting to use
a different binary instead. You should do this only, when you know exactly
what you are doing. If the osm2pgsql version is not compatible, then the
result is undefined.


#### NOMINATIM_WIKIPEDIA_DATA_PATH

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Directory with the wikipedia importance data |
| **Format:**        | path |
| **Default:**       | _empty_ (project directory) |

Set a custom location for the
[wikipedia ranking file](../admin/Import.md#wikipediawikidata-rankings). When
unset, Nominatim expects the data to be saved in the project directory.

#### NOMINATIM_PHRASE_CONFIG

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Configuration file for special phrase imports |
| **Format:**        | path |
| **Default:**       | _empty_ (use default settings) |

The _phrase_config_ file configures black and white lists of tag types,
so that some of them can be ignored, when loading special phrases from
the OSM wiki. The default settings can be found in the configuration
directory as `phrase-settings.json`.

#### NOMINATIM_ADDRESS_LEVEL_CONFIG

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Configuration file for rank assignments |
| **Format:**        | path |
| **Default:**       | _empty_ (use default settings) |

The _address level config_ configures rank assignments for places. See
[Place Ranking](Ranking.md) for a detailed explanation what rank assignments
are and what the configuration file must look like. The default configuration
can be found in the configuration directory as `address-levels.json`.

#### NOMINATIM_IMPORT_STYLE

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Configuration to use for the initial OSM data import |
| **Format:**        | string or path |
| **Default:**       | extratags |

The _style configuration_ describes which OSM objects and tags are taken
into consideration for the search database. This setting may either
be a string pointing to one of the internal styles or it may be a path
pointing to a custom style.

See [Import Styles](Import-Styles.md)
for more information on the available internal styles and the format of the
configuration file.

#### NOMINATIM_FLATNODE_FILE

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Location of osm2pgsql flatnode file |
| **Format:**        | path |
| **Default:**       | _empty_ (do not use a flatnote file) |
| **After Changes:** | Only change when moving the file physically. |

The `osm2pgsql flatnode file` is file that efficiently stores geographic
location for OSM nodes. For larger imports it can significantly speed up
the import. When this option is unset, then osm2pgsql uses a PsotgreSQL table
to store the locations.

!!! warning

    The flatnode file is not only used during the initial import but also
    when adding new data with `nominatim add-data` or `nominatim replication`.
    Make sure you keep the flatnode file around and this setting unmodified,
    if you plan to add more data or run regular updates.


#### NOMINATIM_TABLESPACE_*

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Group of settings for distributing the database over tablespaces |
| **Format:**        | string |
| **Default:**       | _empty_ (do not use a table space) |
| **After Changes:** | no effect after initial import |

Nominatim allows to distribute the search database over up to 10 different
[PostgreSQL tablespaces](https://www.postgresql.org/docs/current/manage-ag-tablespaces.html).
If you use this option, make sure that the tablespaces exist before starting
the import.

The available tablespace groups are:

NOMINATIM_TABLESPACE_SEARCH_DATA
:    Data used by the geocoding frontend.

NOMINATIM_TABLESPACE_SEARCH_INDEX
:    Indexes used by the geocoding frontend.

NOMINATIM_TABLESPACE_OSM_DATA
:    Raw OSM data cache used for import and updates.

NOMINATIM_TABLESPACE_OSM_DATA
:    Indexes on the raw OSM data cache.

NOMINATIM_TABLESPACE_PLACE_DATA
:    Data table with the pre-filtered but still unprocessed OSM data.
     Used only during imports and updates.

NOMINATIM_TABLESPACE_PLACE_INDEX
:    Indexes on raw data table. Used only during imports and updates.

NOMINATIM_TABLESPACE_ADDRESS_DATA
:    Data tables used for computing search terms and addresses of places
     during import and updates.

NOMINATIM_TABLESPACE_ADDRESS_INDEX
:    Indexes on the data tables for search term and address computation.
     Used only for import and updates.

NOMINATIM_TABLESPACE_AUX_DATA
:    Auxiliary data tables for non-OSM data, e.g. for Tiger house number data.

NOMINATIM_TABLESPACE_AUX_INDEX
:    Indexes on auxiliary data tables.


### Replication Update Settings

#### NOMINATIM_REPLICATION_URL

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Base URL of the replication service |
| **Format:**        | url |
| **Default:**       | https://planet.openstreetmap.org/replication/minute |
| **After Changes:** | run `nominatim replication --init` |

Replication services deliver updates to OSM data. Use this setting to choose
which replication service to use. See [Updates](../admin/Update.md) for more
information on how to set up regular updates.

#### NOMINATIM_REPLICATION_MAX_DIFF

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Maximum amount of data to download per update cycle (in MB) |
| **Format:**        | integer |
| **Default:**       | 50 |
| **After Changes:** | restart the replication process |

At each update cycle Nominatim downloads diffs until either no more diffs
are available on the server (i.e. the database is up-to-date) or the limit
given in this setting is exceeded. Nominatim guarantees to downloads at least
one diff, if one is available, no matter how small the setting.

The default for this setting is fairly conservative because Nominatim keeps
all data downloaded in one cycle in RAM. Using large values in a production
server may interfere badly with the search frontend because it evicts data
from RAM that is needed for speedy answers to incoming requests. It is usually
a better idea to keep this setting lower and run multiple update cycles
to catch up with updates.

When catching up in non-production mode, for example after the initial import,
the setting can easily be changed temporarily on the command line:

    NOMINATIM_REPLICATION_MAX_DIFF=3000 nominatim replication


#### NOMINATIM_REPLICATION_UPDATE_INTERVAL

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Publication interval of the replication service (in seconds) |
| **Format:**        | integer |
| **Default:**       | 75 |
| **After Changes:** | restart the replication process |

This setting determines when Nominatim will attempt to download again a new
update. The time is computed from the publication date of the last diff
downloaded. Setting this to a slightly higher value than the actual
publication interval avoids unnecessary rechecks.


#### NOMINATIM_REPLICATION_RECHECK_INTERVAL

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Wait time to recheck for a pending update (in seconds)  |
| **Format:**        | integer |
| **Default:**       | 60 |
| **After Changes:** | restart the replication process |

When replication updates are run in continuous mode (using `nominatim replication`),
this setting determines how long Nominatim waits until it looks for updates
again when updates were not available on the server.

Note that this is different from
[NOMINATIM_REPLICATION_UPDATE_INTERVAL](#nominatim_replication_update_interval).
Nominatim will never attempt to query for new updates for UPDATE_INTERVAL
seconds after the current database date. Only after the update interval has
passed it asks for new data. If then no new data is found, it waits for
RECHECK_INTERVAL seconds before it attempts again.

### API Settings

#### NOMINATIM_CORS_NOACCESSCONTROL

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Send permissive CORS access headers |
| **Format:**        | boolean |
| **Default:**       | yes |
| **After Changes:** | run `nominatim refresh --website` |

When this setting is enabled, API HTTP responses include the HTTP
[CORS](https://en.wikipedia.org/wiki/CORS) headers
`access-control-allow-origin: *` and `access-control-allow-methods: OPTIONS,GET`.

#### NOMINATIM_MAPICON_URL

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | URL prefix for static icon images |
| **Format:**        | url |
| **Default:**       | _empty_ |
| **After Changes:** | run `nominatim refresh --website` |

When a mapicon URL is configured, then Nominatim includes an additional `icon`
field in the responses, pointing to an appropriate icon for the place type.

Map icons used to be included in Nominatim itself but now have moved to the
[nominatim-ui](https://github.com/osm-search/nominatim-ui/) project. If you
want the URL to be included in API responses, make the `/mapicon`
directory of the project available under a public URL and point this setting
to the directory.


#### NOMINATIM_DEFAULT_LANGUAGE

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Language of responses when no language is requested |
| **Format:**        | language code |
| **Default:**       | _empty_ (use the local language of the feature) |
| **After Changes:** | run `nominatim refresh --website` |

Nominatim localizes the place names in responses when the corresponding
translation is available. Users can request a custom language setting through
the HTTP accept-languages header or through the explicit parameter
[accept-languages](../api/Search.md#language-of-results). If neither is
given, it falls back to this setting. If the setting is also empty, then
the local languages (in OSM: the name tag without any language suffix) is
used.


#### NOMINATIM_SEARCH_BATCH_MODE

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Enable a special batch query mode |
| **Format:**        | boolean |
| **Default:**       | no |
| **After Changes:** | run `nominatim refresh --website` |

This feature is currently undocumented and potentially broken.


#### NOMINATIM_SEARCH_NAME_ONLY_THRESHOLD

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Threshold for switching the search index lookup strategy |
| **Format:**        | integer |
| **Default:**       | 500 |
| **After Changes:** | run `nominatim refresh --website` |

This setting defines the threshold over which a name is no longer considered
as rare. When searching for places with rare names, only the name is used
for place lookups. Otherwise the name and any address information is used.

This setting only has an effect after `nominatim refresh --word-counts` has
been called to compute the word frequencies.


#### NOMINATIM_LOOKUP_MAX_COUNT

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Maximum number of OSM ids accepted by /lookup |
| **Format:**        | integer |
| **Default:**       | 50 |
| **After Changes:** | run `nominatim refresh --website` |

The /lookup point accepts list of ids to look up address details for. This
setting restricts the number of places a user may look up with a single
request.


#### NOMINATIM_POLYGON_OUTPUT_MAX_TYPES

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Number of different geometry formats that may be returned |
| **Format:**        | integer |
| **Default:**       | 1 |
| **After Changes:** | run `nominatim refresh --website` |

Nominatim supports returning full geometries of places. The geometries may
be requested in different formats with one of the
[`polygon_*` parameters](../api/Search.md#polygon-output). Use this
setting to restrict the number of geometry types that may be requested
with a single query.

Setting this parameter to 0 disables polygon output completely.

### Logging Settings

#### NOMINATIM_LOG_DB

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Log requests into the database |
| **Format:**        | boolean |
| **Default:**       | no |
| **After Changes:** | run `nominatim refresh --website` |

Enable logging requests into a database table with this setting. The logs
can be found in the table `new_query_log`.

When using this logging method, it is advisable to set up a job that
regularly clears out old logging information. Nominatim will not do that
on its own.

Can be used as the same time as NOMINATIM_LOG_FILE.

#### NOMINATIM_LOG_FILE

| Summary            |                                                     |
| --------------     | --------------------------------------------------- |
| **Description:**   | Log requests into a file |
| **Format:**        | path |
| **Default:**       | _empty_ (logging disabled) |
| **After Changes:** | run `nominatim refresh --website` |

Enable logging of requests into a file with this setting by setting the log
file where to log to. The entries in the log file have the following format:

    <request time> <execution time in s> <number of results> <type> "<query string>"

Request time is the time when the request was started. The execution time is
given in ms and corresponds to the time the query took executing in PHP.
type contains the name of the endpoint used.

Can be used as the same time as NOMINATIM_LOG_DB.

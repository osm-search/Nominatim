<?php
@define('CONST_BasePath', '@CMAKE_SOURCE_DIR@');
@define('CONST_InstallPath', '@CMAKE_BINARY_DIR@');
if (file_exists(getenv('NOMINATIM_SETTINGS'))) require_once(getenv('NOMINATIM_SETTINGS'));
if (file_exists(CONST_InstallPath.'/settings/local.php')) require_once(CONST_InstallPath.'/settings/local.php');
if (isset($_GET['debug']) && $_GET['debug']) @define('CONST_Debug', true);

// General settings
@define('CONST_Debug', false);
@define('CONST_Database_DSN', 'pgsql://@/nominatim'); // <driver>://<username>:<password>@<host>:<port>/<database>
@define('CONST_Database_Web_User', 'www-data');
@define('CONST_Database_Module_Path', CONST_InstallPath.'/module');
@define('CONST_Max_Word_Frequency', '50000');
@define('CONST_Limit_Reindexing', true);
// Restrict search languages.
// Normally Nominatim will include all language variants of name:XX
// in the search index. Set this to a comma separated list of language
// codes, to restrict import to a subset of languages.
// Currently only affects the import of country names and special phrases.
@define('CONST_Languages', false);
// Rules for normalizing terms for comparison before doing comparisons.
// The default is to remove accents and punctuation and to lower-case the
// term. Spaces are kept but collapsed to one standard space.
@define('CONST_Term_Normalization_Rules', ":: NFD (); [[:Nonspacing Mark:] [:Cf:]] >;  :: lower (); [[:Punctuation:][:Space:]]+ > ' '; :: NFC ();");

// Set to false to avoid importing extra postcodes for the US.
@define('CONST_Use_Extra_US_Postcodes', true);
/* Set to true after importing Tiger house number data for the US.
   Note: The tables must already exist or queries will throw errors.
         After changing this setting run ./utils/setup --create-functions
         again. */
@define('CONST_Use_US_Tiger_Data', false);
/* Set to true after importing other external house number data.
   Note: the aux tables must already exist or queries will throw errors.
        After changing this setting run ./utils/setup --create-functions
        again. */
@define('CONST_Use_Aux_Location_data', false);

// Proxy settings
@define('CONST_HTTP_Proxy', false);
@define('CONST_HTTP_Proxy_Host', 'proxy.mydomain.com');
@define('CONST_HTTP_Proxy_Port', '3128');
@define('CONST_HTTP_Proxy_Login', '');
@define('CONST_HTTP_Proxy_Password', '');

// Paths
@define('CONST_ExtraDataPath', CONST_BasePath.'/data');
@define('CONST_Osm2pgsql_Binary', CONST_InstallPath.'/osm2pgsql/osm2pgsql');
@define('CONST_Pyosmium_Binary', '@PYOSMIUM_PATH@');
@define('CONST_Tiger_Data_Path', CONST_ExtraDataPath.'/tiger');
@define('CONST_Wikipedia_Data_Path', CONST_ExtraDataPath);
@define('CONST_Phrase_Config', CONST_BasePath.'/settings/phrase_settings.php');
@define('CONST_Address_Level_Config', CONST_BasePath.'/settings/address-levels.json');
@define('CONST_Import_Style', CONST_BasePath.'/settings/import-full.style');

// osm2pgsql settings
@define('CONST_Osm2pgsql_Flatnode_File', null);

// tablespace settings
// osm2pgsql caching tables (aka slim mode tables) - update only
@define('CONST_Tablespace_Osm2pgsql_Data', false);
@define('CONST_Tablespace_Osm2pgsql_Index', false);
// osm2pgsql output tables (aka main table) - update only
@define('CONST_Tablespace_Place_Data', false);
@define('CONST_Tablespace_Place_Index', false);
// address computation tables - update only
@define('CONST_Tablespace_Address_Data', false);
@define('CONST_Tablespace_Address_Index', false);
// search tables - needed for lookups
@define('CONST_Tablespace_Search_Data', false);
@define('CONST_Tablespace_Search_Index', false);
// additional data, e.g. TIGER data, type searches - needed for lookups
@define('CONST_Tablespace_Aux_Data', false);
@define('CONST_Tablespace_Aux_Index', false);

//// Replication settings

// Base URL of replication service
@define('CONST_Replication_Url', 'https://planet.openstreetmap.org/replication/minute');

// Maximum size in MB of data to download per batch
@define('CONST_Replication_Max_Diff_size', '30');
// How long until the service publishes the next diff
// (relative to the age of data in the diff).
@define('CONST_Replication_Update_Interval', '75');
// How long to sleep when no update could be found
@define('CONST_Replication_Recheck_Interval', '60');

// Website settings
@define('CONST_NoAccessControl', true);

@define('CONST_Website_BaseURL', 'http://'.php_uname('n').'/');
// Language to assume when none is supplied with the query.
// When set to false, the local language (i.e. the name tag without suffix)
// will be used.
@define('CONST_Default_Language', false);
// Appearance of the map in the debug interface.
@define('CONST_Default_Lat', 20.0);
@define('CONST_Default_Lon', 0.0);
@define('CONST_Default_Zoom', 2);
@define('CONST_Map_Tile_URL', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
@define('CONST_Map_Tile_Attribution', ''); // Set if tile source isn't osm.org

@define('CONST_Search_AreaPolygons', true);

@define('CONST_Search_BatchMode', false);

@define('CONST_Search_NameOnlySearchFrequencyThreshold', 500);
// If set to true, then reverse order of queries will be tried by default.
// When set to false only selected languages alloow reverse search.
@define('CONST_Search_ReversePlanForAll', true);

// Maximum number of OSM ids that may be queried at once
// for the places endpoint.
@define('CONST_Places_Max_ID_count', 50);

// Number of different geometry formats that may be queried in parallel.
// Set to zero to disable polygon output.
@define('CONST_PolygonOutput_MaximumTypes', 1);

// Log settings
// Set to true to log into new_query_log table.
// You should set up a cron job that regularly clears out this table.
@define('CONST_Log_DB', false);
// Set to a file name to enable logging to a file.
@define('CONST_Log_File', false);

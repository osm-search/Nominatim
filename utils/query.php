<?php

require_once(CONST_LibDir.'/init-cmd.php');
require_once(CONST_LibDir.'/Geocode.php');
require_once(CONST_LibDir.'/ParameterParser.php');
ini_set('memory_limit', '800M');

$aCMDOptions
= array(
   'Query database from command line. Returns search result as JSON.',
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

   array('search', '', 0, 1, 1, 1, 'string', 'Search for given term or coordinate'),
   array('country', '', 0, 1, 1, 1, 'string', 'Structured search: country'),
   array('state', '', 0, 1, 1, 1, 'string', 'Structured search: state'),
   array('county', '', 0, 1, 1, 1, 'string', 'Structured search: county'),
   array('city', '', 0, 1, 1, 1, 'string', 'Structured search: city'),
   array('street', '', 0, 1, 1, 1, 'string', 'Structured search: street'),
   array('amenity', '', 0, 1, 1, 1, 'string', 'Structured search: amenity'),
   array('postalcode', '', 0, 1, 1, 1, 'string', 'Structured search: postal code'),

   array('accept-language', '', 0, 1, 1, 1, 'string', 'Preferred language order for showing search results'),
   array('bounded', '', 0, 1, 0, 0, 'bool', 'Restrict results to given viewbox'),
   array('nodedupe', '', 0, 1, 0, 0, 'bool', 'Do not remove duplicate results'),
   array('limit', '', 0, 1, 1, 1, 'int', 'Maximum number of results returned (default: 10)'),
   array('exclude_place_ids', '', 0, 1, 1, 1, 'string', 'Comma-separated list of place ids to exclude from results'),
   array('featureType', '', 0, 1, 1, 1, 'string', 'Restrict results to certain features (country, state,city,settlement)'),
   array('countrycodes', '', 0, 1, 1, 1, 'string', 'Comma-separated list of countries to restrict search to'),
   array('viewbox', '', 0, 1, 1, 1, 'string', 'Prefer results in given view box'),

   array('project-dir', '', 0, 1, 1, 1, 'realpath', 'Base directory of the Nominatim installation (default: .)'),
  );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

loadSettings($aCMDResult['project-dir'] ?? getcwd());
@define('CONST_Database_DSN', getSetting('DATABASE_DSN'));
@define('CONST_Default_Language', getSetting('DEFAULT_LANGUAGE', false));
@define('CONST_Log_DB', getSettingBool('LOG_DB'));
@define('CONST_Log_File', getSetting('LOG_FILE', false));
@define('CONST_Max_Word_Frequency', getSetting('MAX_WORD_FREQUENCY'));
@define('CONST_NoAccessControl', getSettingBool('CORS_NOACCESSCONTROL'));
@define('CONST_Places_Max_ID_count', getSetting('LOOKUP_MAX_COUNT'));
@define('CONST_PolygonOutput_MaximumTypes', getSetting('POLYGON_OUTPUT_MAX_TYPES'));
@define('CONST_Search_BatchMode', getSettingBool('SEARCH_BATCH_MODE'));
@define('CONST_Search_NameOnlySearchFrequencyThreshold', getSetting('SEARCH_NAME_ONLY_THRESHOLD'));
@define('CONST_Term_Normalization_Rules', getSetting('TERM_NORMALIZATION'));
@define('CONST_Use_Aux_Location_data', getSettingBool('USE_AUX_LOCATION_DATA'));
@define('CONST_Use_US_Tiger_Data', getSettingBool('USE_US_TIGER_DATA'));
@define('CONST_MapIcon_URL', getSetting('MAPICON_URL', false));


$oDB = new Nominatim\DB;
$oDB->connect();

if (isset($aCMDResult['nodedupe'])) $aCMDResult['dedupe'] = 'false';

$oParams = new Nominatim\ParameterParser($aCMDResult);

$aSearchParams = array(
                     'search',
                     'amenity',
                     'street',
                     'city',
                     'county',
                     'state',
                     'country',
                     'postalcode'
                 );

if (!$oParams->hasSetAny($aSearchParams)) {
    showUsage($aCMDOptions, true);
    return 1;
}

$oGeocode = new Nominatim\Geocode($oDB);

$oGeocode->setLanguagePreference($oParams->getPreferredLanguages(false));
$oGeocode->setReverseInPlan(true);
$oGeocode->loadParamArray($oParams);

if ($oParams->getBool('search')) {
    $oGeocode->setQuery($aCMDResult['search']);
} else {
    $oGeocode->setQueryFromParams($oParams);
}

$aSearchResults = $oGeocode->lookup();

echo json_encode($aSearchResults, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)."\n";

<?php

require_once(CONST_BasePath.'/lib/init-cmd.php');
require_once(CONST_BasePath.'/lib/Geocode.php');
require_once(CONST_BasePath.'/lib/ParameterParser.php');
ini_set('memory_limit', '800M');

$aCMDOptions
= array(
   'Query database from command line. Returns search result as JSON.',
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

   array('search', '', 0, 1, 1, 1, 'string', 'Search for given term or coordinate'),

   array('accept-language', '', 0, 1, 1, 1, 'string', 'Preferred language order for showing search results'),
   array('bounded', '', 0, 1, 0, 0, 'bool', 'Restrict results to given viewbox'),
   array('nodedupe', '', 0, 1, 0, 0, 'bool', 'Do not remove duplicate results'),
   array('limit', '', 0, 1, 1, 1, 'int', 'Maximum number of results returned (default: 10)'),
   array('exclude_place_ids', '', 0, 1, 1, 1, 'string', 'Comma-separated list of place ids to exclude from results'),
   array('featureType', '', 0, 1, 1, 1, 'string', 'Restrict results to certain features (country, state,city,settlement)'),
   array('countrycodes', '', 0, 1, 1, 1, 'string', 'Comma-separated list of countries to restrict search to'),
   array('viewbox', '', 0, 1, 1, 1, 'string', 'Prefer results in given view box')
  );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

$oDB =& getDB();
$oParams = new Nominatim\ParameterParser($aCMDResult);

if ($oParams->getBool('search')) {
    if (isset($aCMDResult['nodedupe'])) $aCMDResult['dedupe'] = 'false';

    $oGeocode = new Nominatim\Geocode($oDB);

    $oGeocode->setLanguagePreference($oParams->getPreferredLanguages(false));
    $oGeocode->loadParamArray($oParams);
    $oGeocode->setQuery($aCMDResult['search']);

    $aSearchResults = $oGeocode->lookup();

    if (version_compare(phpversion(), '5.4.0', '<')) {
        echo json_encode($aSearchResults);
    } else {
        echo json_encode($aSearchResults, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)."\n";
    }
} else {
    showUsage($aCMDOptions, true);
}

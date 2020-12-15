<?php

require_once(CONST_LibDir.'/init-website.php');
require_once(CONST_LibDir.'/log.php');
require_once(CONST_LibDir.'/Geocode.php');
require_once(CONST_LibDir.'/output.php');
ini_set('memory_limit', '200M');

$oDB = new Nominatim\DB(CONST_Database_DSN);
$oDB->connect();
$oParams = new Nominatim\ParameterParser();

$oGeocode = new Nominatim\Geocode($oDB);

$aLangPrefOrder = $oParams->getPreferredLanguages();
$oGeocode->setLanguagePreference($aLangPrefOrder);

if (CONST_Search_ReversePlanForAll
    || isset($aLangPrefOrder['name:de'])
    || isset($aLangPrefOrder['name:ru'])
    || isset($aLangPrefOrder['name:ja'])
    || isset($aLangPrefOrder['name:pl'])
) {
    $oGeocode->setReverseInPlan(true);
}

// Format for output
$sOutputFormat = $oParams->getSet('format', array('xml', 'json', 'jsonv2', 'geojson', 'geocodejson'), 'jsonv2');
set_exception_handler_by_format($sOutputFormat);

$oGeocode->loadParamArray($oParams, null);

if (CONST_Search_BatchMode && isset($_GET['batch'])) {
    $aBatch = json_decode($_GET['batch'], true);
    $aBatchResults = array();
    foreach ($aBatch as $aBatchParams) {
        $oBatchGeocode = clone $oGeocode;
        $oBatchParams = new Nominatim\ParameterParser($aBatchParams);
        $oBatchGeocode->loadParamArray($oBatchParams);
        $oBatchGeocode->setQueryFromParams($oBatchParams);
        $aSearchResults = $oBatchGeocode->lookup();
        $aBatchResults[] = $aSearchResults;
    }
    include(CONST_LibDir.'/template/search-batch-json.php');
    exit;
}

$oGeocode->setQueryFromParams($oParams);

if (!$oGeocode->getQueryString()
    && isset($_SERVER['PATH_INFO'])
    && strlen($_SERVER['PATH_INFO']) > 0
    && $_SERVER['PATH_INFO'][0] == '/'
) {
    $sQuery = substr(rawurldecode($_SERVER['PATH_INFO']), 1);

    // reverse order of '/' separated string
    $aPhrases = explode('/', $sQuery);
    $aPhrases = array_reverse($aPhrases);
    $sQuery = join(', ', $aPhrases);
    $oGeocode->setQuery($sQuery);
}

$hLog = logStart($oDB, 'search', $oGeocode->getQueryString(), $aLangPrefOrder);

$aSearchResults = $oGeocode->lookup();

logEnd($oDB, $hLog, count($aSearchResults));

$sQuery = $oGeocode->getQueryString();

$aMoreParams = $oGeocode->getMoreUrlParams();
$aMoreParams['format'] = $sOutputFormat;
if (isset($_SERVER['HTTP_ACCEPT_LANGUAGE'])) {
    $aMoreParams['accept-language'] = $_SERVER['HTTP_ACCEPT_LANGUAGE'];
}

if (isset($_SERVER['REQUEST_SCHEME'])
    && isset($_SERVER['SERVER_NAME'])
    && isset($_SERVER['DOCUMENT_URI'])
) {
    $sMoreURL = $_SERVER['REQUEST_SCHEME'].'://'
                .$_SERVER['SERVER_NAME'].$_SERVER['DOCUMENT_URI'].'/?'
                .http_build_query($aMoreParams);
} else {
    $sMoreURL = '/search.php'.http_build_query($aMoreParams);
}

if (CONST_Debug) exit;

$sOutputTemplate = ($sOutputFormat == 'jsonv2') ? 'json' : $sOutputFormat;
include(CONST_LibDir.'/template/search-'.$sOutputTemplate.'.php');

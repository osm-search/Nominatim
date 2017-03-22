<?php
@define('CONST_ConnectionBucket_PageType', 'Search');

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/Geocode.php');
require_once(CONST_BasePath.'/lib/output.php');
ini_set('memory_limit', '200M');

$oDB =& getDB();
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
$sOutputFormat = $oParams->getSet('format', array('html', 'xml', 'json', 'jsonv2'), 'html');

// Show / use polygons
if ($sOutputFormat == 'html') {
    $oGeocode->setIncludePolygonAsGeoJSON($oParams->getBool('polygon_geojson'));
    $bAsGeoJSON = false;
} else {
    $bAsPoints = $oParams->getBool('polygon');
    $bAsGeoJSON = $oParams->getBool('polygon_geojson');
    $bAsKML = $oParams->getBool('polygon_kml');
    $bAsSVG = $oParams->getBool('polygon_svg');
    $bAsText = $oParams->getBool('polygon_text');
    $iWantedTypes = ($bAsGeoJSON?1:0) + ($bAsKML?1:0) + ($bAsSVG?1:0) + ($bAsText?1:0) + ($bAsPoints?1:0);
    if ($iWantedTypes > CONST_PolygonOutput_MaximumTypes) {
        if (CONST_PolygonOutput_MaximumTypes) {
            userError("Select only ".CONST_PolygonOutput_MaximumTypes." polgyon output option");
        } else {
            userError("Polygon output is disabled");
        }
        exit;
    }
    $oGeocode->setIncludePolygonAsPoints($bAsPoints);
    $oGeocode->setIncludePolygonAsText($bAsText);
    $oGeocode->setIncludePolygonAsGeoJSON($bAsGeoJSON);
    $oGeocode->setIncludePolygonAsKML($bAsKML);
    $oGeocode->setIncludePolygonAsSVG($bAsSVG);
}

// Polygon simplification threshold (optional)
$oGeocode->setPolygonSimplificationThreshold($oParams->getFloat('polygon_threshold', 0.0));

$oGeocode->loadParamArray($oParams);

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
    include(CONST_BasePath.'/lib/template/search-batch-json.php');
    exit;
}

$oGeocode->setQueryFromParams($oParams);

if (!$oGeocode->getQueryString()
    && isset($_SERVER['PATH_INFO'])
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

if ($sOutputFormat=='html') {
    $sDataDate = chksql($oDB->getOne("select TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1"));
}
logEnd($oDB, $hLog, sizeof($aSearchResults));

$sQuery = $oGeocode->getQueryString();

$aMoreParams = $oGeocode->getMoreUrlParams();
if ($sOutputFormat != 'html') $aMoreParams['format'] = $sOutputFormat;
if (isset($_SERVER["HTTP_ACCEPT_LANGUAGE"])) {
    $aMoreParams['accept-language'] = $_SERVER["HTTP_ACCEPT_LANGUAGE"];
}
$sMoreURL = CONST_Website_BaseURL.'search.php?'.http_build_query($aMoreParams);

if (CONST_Debug) exit;

include(CONST_BasePath.'/lib/template/search-'.$sOutputFormat.'.php');

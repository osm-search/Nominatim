<?php
@define('CONST_ConnectionBucket_PageType', 'Reverse');

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/PlaceLookup.php');
require_once(CONST_BasePath.'/lib/ReverseGeocode.php');
require_once(CONST_BasePath.'/lib/output.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();

$bAsGeoJSON = $oParams->getBool('polygon_geojson');
$bAsKML = $oParams->getBool('polygon_kml');
$bAsSVG = $oParams->getBool('polygon_svg');
$bAsText = $oParams->getBool('polygon_text');

$iWantedTypes = ($bAsGeoJSON?1:0) + ($bAsKML?1:0) + ($bAsSVG?1:0) + ($bAsText?1:0);
if ($iWantedTypes > CONST_PolygonOutput_MaximumTypes) {
    if (CONST_PolygonOutput_MaximumTypes) {
        userError("Select only ".CONST_PolygonOutput_MaximumTypes." polgyon output option");
    } else {
        userError("Polygon output is disabled");
    }
}

// Polygon simplification threshold (optional)
$fThreshold = $oParams->getFloat('polygon_threshold', 0.0);

// Format for output
$sOutputFormat = $oParams->getSet('format', array('html', 'xml', 'json', 'jsonv2'), 'xml');

// Preferred language
$aLangPrefOrder = $oParams->getPreferredLanguages();

$oDB =& getDB();

$hLog = logStart($oDB, 'reverse', $_SERVER['QUERY_STRING'], $aLangPrefOrder);


$oPlaceLookup = new Nominatim\PlaceLookup($oDB);
$oPlaceLookup->setLanguagePreference($aLangPrefOrder);
$oPlaceLookup->setIncludeAddressDetails($oParams->getBool('addressdetails', true));
$oPlaceLookup->setIncludeExtraTags($oParams->getBool('extratags', false));
$oPlaceLookup->setIncludeNameDetails($oParams->getBool('namedetails', false));

$sOsmType = $oParams->getSet('osm_type', array('N', 'W', 'R'));
$iOsmId = $oParams->getInt('osm_id', -1);
$fLat = $oParams->getFloat('lat');
$fLon = $oParams->getFloat('lon');
if ($sOsmType && $iOsmId > 0) {
    $aPlace = $oPlaceLookup->lookupOSMID($sOsmType, $iOsmId);
} elseif ($fLat !== false && $fLon !== false) {
    $oReverseGeocode = new Nominatim\ReverseGeocode($oDB);
    $oReverseGeocode->setZoom($oParams->getInt('zoom', 18));

    $aLookup = $oReverseGeocode->lookup($fLat, $fLon);
    if (CONST_Debug) var_dump($aLookup);

    $aPlace = $oPlaceLookup->lookup(
        (int)$aLookup['place_id'],
        $aLookup['type'],
        $aLookup['fraction']
    );
} elseif ($sOutputFormat != 'html') {
    userError("Need coordinates or OSM object to lookup.");
}

if (isset($aPlace)) {
    $oPlaceLookup->setIncludePolygonAsPoints(false);
    $oPlaceLookup->setIncludePolygonAsText($bAsText);
    $oPlaceLookup->setIncludePolygonAsGeoJSON($bAsGeoJSON);
    $oPlaceLookup->setIncludePolygonAsKML($bAsKML);
    $oPlaceLookup->setIncludePolygonAsSVG($bAsSVG);
    $oPlaceLookup->setPolygonSimplificationThreshold($fThreshold);

    $fRadius = $fDiameter = getResultDiameter($aPlace);
    $aOutlineResult = $oPlaceLookup->getOutlines(
        $aPlace['place_id'],
        $aPlace['lon'],
        $aPlace['lat'],
        $fRadius
    );

    if ($aOutlineResult) {
        $aPlace = array_merge($aPlace, $aOutlineResult);
    }
}


if (CONST_Debug) {
    var_dump($aPlace);
    exit;
}

if ($sOutputFormat=='html') {
    $sDataDate = chksql($oDB->getOne("select TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1"));
    $sTileURL = CONST_Map_Tile_URL;
    $sTileAttribution = CONST_Map_Tile_Attribution;
}
include(CONST_BasePath.'/lib/template/address-'.$sOutputFormat.'.php');

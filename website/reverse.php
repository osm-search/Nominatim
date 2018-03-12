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

// Format for output
$sOutputFormat = $oParams->getSet('format', array('html', 'xml', 'json', 'jsonv2'), 'xml');

// Preferred language
$aLangPrefOrder = $oParams->getPreferredLanguages();

$oDB =& getDB();

$hLog = logStart($oDB, 'reverse', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

$oPlaceLookup = new Nominatim\PlaceLookup($oDB);
$oPlaceLookup->loadParamArray($oParams);

$sOsmType = $oParams->getSet('osm_type', array('N', 'W', 'R'));
$iOsmId = $oParams->getInt('osm_id', -1);
$fLat = $oParams->getFloat('lat');
$fLon = $oParams->getFloat('lon');
$iZoom = $oParams->getInt('zoom', 18);

if ($sOsmType && $iOsmId > 0) {
    $aPlace = $oPlaceLookup->lookupOSMID($sOsmType, $iOsmId);
} elseif ($fLat !== false && $fLon !== false) {
    $oReverseGeocode = new Nominatim\ReverseGeocode($oDB);
    $oReverseGeocode->setZoom($iZoom);

    $oLookup = $oReverseGeocode->lookup($fLat, $fLon);
    if (CONST_Debug) var_dump($oLookup);

    if ($oLookup) {
        $aPlaces = $oPlaceLookup->lookup(array($oLookup->iId => $oLookup));
        if (sizeof($aPlaces)) {
            $aPlace = reset($aPlaces);
        }
    }
} elseif ($sOutputFormat != 'html') {
    userError('Need coordinates or OSM object to lookup.', $sOutputFormat);
}

if (isset($aPlace)) {
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
} else {
    $aPlace = [];
}


if (CONST_Debug) {
    var_dump($aPlace);
    exit;
}

if ($sOutputFormat == 'html') {
    $sDataDate = chksql($oDB->getOne("select TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1"));
    $sTileURL = CONST_Map_Tile_URL;
    $sTileAttribution = CONST_Map_Tile_Attribution;
}
include(CONST_BasePath.'/lib/template/address-'.$sOutputFormat.'.php');

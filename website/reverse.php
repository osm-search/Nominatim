<?php

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/PlaceLookup.php');
require_once(CONST_BasePath.'/lib/ReverseGeocode.php');
require_once(CONST_BasePath.'/lib/output.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();

// Format for output
$sOutputFormat = $oParams->getSet('format', array('html', 'xml', 'json', 'jsonv2', 'geojson', 'geocodejson'), 'xml');
set_exception_handler_by_format($sOutputFormat);

// Preferred language
$aLangPrefOrder = $oParams->getPreferredLanguages();

$oDB =& getDB();

$hLog = logStart($oDB, 'reverse', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

$oPlaceLookup = new Nominatim\PlaceLookup($oDB);
$oPlaceLookup->loadParamArray($oParams);
$oPlaceLookup->setIncludeAddressDetails($oParams->getBool('addressdetails', true));

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
        if (!empty($aPlaces)) {
            $aPlace = reset($aPlaces);
        }
    }
} elseif ($sOutputFormat != 'html') {
    userError('Need coordinates or OSM object to lookup.');
}

if (isset($aPlace)) {
    $aOutlineResult = $oPlaceLookup->getOutlines(
        $aPlace['place_id'],
        $aPlace['lon'],
        $aPlace['lat'],
        Nominatim\ClassTypes\getProperty($aPlace, 'defdiameter', 0.0001),
        $fLat,
        $fLon
    );

    if ($aOutlineResult) {
        $aPlace = array_merge($aPlace, $aOutlineResult);
    }
} else {
    $aPlace = array();
}


if (CONST_Debug) {
    var_dump($aPlace);
    exit;
}

if ($sOutputFormat == 'html') {
    $sDataDate = chksql($oDB->getOne("select TO_CHAR(lastimportdate,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1"));
    $sTileURL = CONST_Map_Tile_URL;
    $sTileAttribution = CONST_Map_Tile_Attribution;
} elseif ($sOutputFormat == 'geocodejson') {
    $sQuery = $fLat.','.$fLon;
    if (isset($aPlace['place_id'])) {
        $fDistance = chksql($oDB->getOne('SELECT ST_Distance(ST_SetSRID(ST_Point('.$fLon.','.$fLat.'),4326), centroid) FROM placex where place_id='.$aPlace['place_id']));
    }
}

$sOutputTemplate = ($sOutputFormat == 'jsonv2') ? 'json' : $sOutputFormat;
include(CONST_BasePath.'/lib/template/address-'.$sOutputTemplate.'.php');

<?php

require_once(CONST_LibDir.'/init-website.php');
require_once(CONST_LibDir.'/log.php');
require_once(CONST_LibDir.'/PlaceLookup.php');
require_once(CONST_LibDir.'/ReverseGeocode.php');
require_once(CONST_LibDir.'/output.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();

// Format for output
$sOutputFormat = $oParams->getSet('format', array('xml', 'json', 'jsonv2', 'geojson', 'geocodejson'), 'xml');
set_exception_handler_by_format($sOutputFormat);

// Preferred language
$aLangPrefOrder = $oParams->getPreferredLanguages();

$oDB = new Nominatim\DB();
$oDB->connect();

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

    if ($oLookup) {
        $aPlaces = $oPlaceLookup->lookup(array($oLookup->iId => $oLookup));
        if (!empty($aPlaces)) {
            $aPlace = reset($aPlaces);
        }
    }
} else {
    userError('Need coordinates or OSM object to lookup.');
}

if (isset($aPlace)) {
    $aOutlineResult = $oPlaceLookup->getOutlines(
        $aPlace['place_id'],
        $aPlace['lon'],
        $aPlace['lat'],
        Nominatim\ClassTypes\getDefRadius($aPlace),
        $fLat,
        $fLon
    );

    if ($aOutlineResult) {
        $aPlace = array_merge($aPlace, $aOutlineResult);
    }
} else {
    $aPlace = array();
}

logEnd($oDB, $hLog, count($aPlace) ? 1 : 0);

if (CONST_Debug) {
    var_dump($aPlace);
    exit;
}

if ($sOutputFormat == 'geocodejson') {
    $sQuery = $fLat.','.$fLon;
    if (isset($aPlace['place_id'])) {
        $fDistance = $oDB->getOne(
            'SELECT ST_Distance(ST_SetSRID(ST_Point(:lon,:lat),4326), centroid) FROM placex where place_id = :placeid',
            array(':lon' => $fLon, ':lat' => $fLat, ':placeid' => $aPlace['place_id'])
        );
    }
}

$sOutputTemplate = ($sOutputFormat == 'jsonv2') ? 'json' : $sOutputFormat;
include(CONST_LibDir.'/template/address-'.$sOutputTemplate.'.php');

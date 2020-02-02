<?php

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/PlaceLookup.php');
require_once(CONST_BasePath.'/lib/ReverseGeocode.php');
require_once(CONST_BasePath.'/lib/output.php');
ini_set('memory_limit', '200M');


$oParams = new Nominatim\ParameterParser();
$oDB = new Nominatim\DB();
$oDB->connect();

// Preferred language (need it to see readable name of place)
$aLangPrefOrder = $oParams->getPreferredLanguages();
$sLanguagePrefArraySQL = $oDB->getArraySQL($oDB->getDBQuotedList($aLangPrefOrder));


$oPlaceLookup = new Nominatim\PlaceLookup($oDB);
$oPlaceLookup->loadParamArray($oParams);
$oPlaceLookup->setIncludeAddressDetails($oParams->getBool('addressdetails', true));


$fLat = $oParams->getFloat('lat');
$fLon = $oParams->getFloat('lon');
$iZoom = $oParams->getInt('zoom', 18);


if ($fLat !== false && $fLon !== false) {
    $oReverseGeocode = new Nominatim\ReverseGeocode($oDB);
    $aPlaces = $oReverseGeocode->getAllZoomLevels($fLat, $fLon, $sLanguagePrefArraySQL);
    javascript_renderData($aPlaces);
} else {
    userError('Need coordinates to lookup.');
}


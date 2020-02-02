<?php

require_once(CONST_BasePath . '/lib/init-website.php');
require_once(CONST_BasePath . '/lib/output.php');
require_once(CONST_BasePath . '/lib/PlaceLookup.php');
ini_set('memory_limit', '200M');

$aParams = new Nominatim\ParameterParser();

$oDB = new Nominatim\DB();
$oDB->connect();

$sLanguagePrefArraySQL = $oDB->getArraySQL($aParams->getPreferredLanguages());

$oPlaceLookup = new Nominatim\PlaceLookup($oDB);
$oPlaceLookup->loadParamArray($aParams);
$oPlaceLookup->setIncludeAddressDetails(true);

$sOsmId = $aParams->getString('osm_id');
$sOsmType = $aParams->getString('osm_type', null);
if (!$sOsmId) userError('Please send osm id');

$aPlace = getPlaceByType($oPlaceLookup, $sOsmId, $sOsmType);
if ($aPlace) {
    //add outlines data
    $aPlace = array_merge($aPlace, getOutlines($oPlaceLookup, $aPlace));

    //add wiki, address and center data
    $aPlace = array_merge($aPlace, getExtraJsonFields($oDB, $aPlace['place_id']));
    javascript_renderData($aPlace);
}


function getPlaceByType($oPlaceLookup, $sOsmId, $sOsmType = null)
{
    if(!is_null($sOsmType)) {
        return  $oPlaceLookup->lookupOSMID($sOsmType, $sOsmId);
    }
    $aTypes = ['N', 'R', 'W'];
    foreach ($aTypes as $sType) {
        $aPlace = $oPlaceLookup->lookupOSMID($sType, $sOsmId);
        if ($aPlace) return $aPlace;
    }
}


function getOutlines($oPlaceLookup, $aPlace)
{
    $outlines =  $oPlaceLookup->getOutlines(
        $aPlace['place_id'],
        $aPlace['lon'],
        $aPlace['lat'],
        Nominatim\ClassTypes\getProperty($aPlace, 'defdiameter', 0.0001)
    );
    return $outlines ? $outlines : [];
}

function getExtraJsonFields($oDB, $iPlaceID) {
    $formatted = [];
    $sSQL = "SELECT address::json, extratags::json as wiki, ST_AsGeoJSON(centroid)::json as center FROM placex  WHERE place_id = $iPlaceID";
    $res = $oDB->getRow($sSQL);
    if($res && is_array($res)) {
        foreach ($res as $key => $value) {
            $formatted[$key] = json_decode($value, true);
        }
    }
    return $formatted;
}

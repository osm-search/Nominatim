<?php

require_once(CONST_LibDir.'/init-website.php');
require_once(CONST_LibDir.'/log.php');
require_once(CONST_LibDir.'/PlaceLookup.php');
require_once(CONST_LibDir.'/output.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();

// Format for output
$sOutputFormat = $oParams->getSet('format', array('xml', 'json', 'jsonv2', 'geojson', 'geocodejson'), 'xml');
set_exception_handler_by_format($sOutputFormat);

// Preferred language
$aLangPrefOrder = $oParams->getPreferredLanguages();

$oDB = new Nominatim\DB(CONST_Database_DSN);
$oDB->connect();

$hLog = logStart($oDB, 'place', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

$aSearchResults = array();
$aCleanedQueryParts = array();

$oPlaceLookup = new Nominatim\PlaceLookup($oDB);
$oPlaceLookup->loadParamArray($oParams);
$oPlaceLookup->setIncludeAddressDetails($oParams->getBool('addressdetails', true));

$aOsmIds = explode(',', $oParams->getString('osm_ids', ''));

if (count($aOsmIds) > CONST_Places_Max_ID_count) {
    userError('Bulk User: Only ' . CONST_Places_Max_ID_count . ' ids are allowed in one request.');
}

foreach ($aOsmIds as $sItem) {
    // Skip empty sItem
    if (empty($sItem)) continue;
    
    $sType = $sItem[0];
    $iId = (int) substr($sItem, 1);
    if ($iId > 0 && ($sType == 'N' || $sType == 'W' || $sType == 'R')) {
        $aCleanedQueryParts[] = $sType . $iId;
        $oPlace = $oPlaceLookup->lookupOSMID($sType, $iId);
        if ($oPlace) {
            // we want to use the search-* output templates, so we need to fill
            // $aSearchResults and slightly change the (reverse search) oPlace
            // key names
            $oResult = $oPlace;
            unset($oResult['aAddress']);
            if (isset($oPlace['aAddress'])) $oResult['address'] = $oPlace['aAddress'];
            if ($sOutputFormat != 'geocodejson') {
                unset($oResult['langaddress']);
                $oResult['name'] = $oPlace['langaddress'];
            }

            $aOutlineResult = $oPlaceLookup->getOutlines(
                $oPlace['place_id'],
                $oPlace['lon'],
                $oPlace['lat'],
                Nominatim\ClassTypes\getDefRadius($oPlace)
            );

            if ($aOutlineResult) {
                $oResult = array_merge($oResult, $aOutlineResult);
            }

            $aSearchResults[] = $oResult;
        }
    }
}


if (CONST_Debug) exit;

$sXmlRootTag = 'lookupresults';
$sQuery = join(',', $aCleanedQueryParts);
// we initialize these to avoid warnings in our logfile
$sViewBox = '';
$bShowPolygons = '';
$aExcludePlaceIDs = array();
$sMoreURL = '';

logEnd($oDB, $hLog, 1);

$sOutputTemplate = ($sOutputFormat == 'jsonv2') ? 'json' : $sOutputFormat;
include(CONST_LibDir.'/template/search-'.$sOutputTemplate.'.php');

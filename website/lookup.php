<?php

@define('CONST_ConnectionBucket_PageType', 'Reverse');

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/PlaceLookup.php');
require_once(CONST_BasePath.'/lib/output.php');

$oDB =& getDB();
ini_set('memory_limit', '200M');

// Format for output
$sOutputFormat = getParamSet('format', array('xml', 'json'), 'xml');

// Preferred language
$aLangPrefOrder = getPreferredLanguages();

$hLog = logStart($oDB, 'place', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

$aSearchResults = array();
$aCleanedQueryParts = array();

$oPlaceLookup = new PlaceLookup($oDB);
$oPlaceLookup->setLanguagePreference($aLangPrefOrder);
$oPlaceLookup->setIncludeAddressDetails(getParamBool('addressdetails', true));
$oPlaceLookup->setIncludeExtraTags(getParamBool('extratags', false));
$oPlaceLookup->setIncludeNameDetails(getParamBool('namedetails', false));

$aOsmIds = explode(',', getParamString('osm_ids', ''));

if (count($aOsmIds) > CONST_Places_Max_ID_count)
{
	userError('Bulk User: Only ' . CONST_Places_Max_ID_count . " ids are allowed in one request.");
}

foreach ($aOsmIds AS $sItem)
{
	// Skip empty sItem
	if (empty($sItem)) continue;
	
	$sType = $sItem[0];
	$iId = (int) substr($sItem, 1);
	if ( $iId > 0 && ($sType == 'N' || $sType == 'W' || $sType == 'R') )
	{
		$aCleanedQueryParts[] = $sType . $iId;
		$oPlace = $oPlaceLookup->lookupOSMID($sType, $iId);
		if ($oPlace){
			// we want to use the search-* output templates, so we need to fill
			// $aSearchResults and slightly change the (reverse search) oPlace
			// key names
			$oResult = $oPlace;
			unset($oResult['aAddress']);
			if (isset($oPlace['aAddress'])) $oResult['address'] = $oPlace['aAddress'];
			unset($oResult['langaddress']);
			$oResult['name'] = $oPlace['langaddress'];
			$aSearchResults[] = $oResult;
		}
	}
}


if (CONST_Debug) exit;

$sXmlRootTag = 'lookupresults';
$sQuery = join(',',$aCleanedQueryParts);
// we initialize these to avoid warnings in our logfile
$sViewBox = '';
$bShowPolygons = '';
$aExcludePlaceIDs = [];
$sMoreURL = '';

include(CONST_BasePath.'/lib/template/search-'.$sOutputFormat.'.php');

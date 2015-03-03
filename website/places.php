<?php
	@define('CONST_ConnectionBucket_PageType', 'Reverse');

	require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
	require_once(CONST_BasePath.'/lib/log.php');
	require_once(CONST_BasePath.'/lib/PlaceLookup.php');

	if (strpos(CONST_BulkUserIPs, ','.$_SERVER["REMOTE_ADDR"].',') !== false)
	{
		$fLoadAvg = getLoadAverage();
		if ($fLoadAvg > 2) sleep(60);
		if ($fLoadAvg > 4) sleep(120);
		if ($fLoadAvg > 6)
		{
			userError("Bulk User: Temporary block due to high server load");
			exit;
		}
	}

	$oDB =& getDB();
	ini_set('memory_limit', '200M');

	// Format for output
	$sOutputFormat = 'xml';
	if (isset($_GET['format']) && ($_GET['format'] == 'xml' || $_GET['format'] == 'json'))
	{
		$sOutputFormat = $_GET['format'];
	}

	// Show address breakdown
	$bShowAddressDetails = true;
	if (isset($_GET['addressdetails'])) $bShowAddressDetails = (bool)$_GET['addressdetails'];

	// Preferred language
	$aLangPrefOrder = getPreferredLanguages();

	$hLog = logStart($oDB, 'place', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

	if (isset($_GET['osm_ids']))
	{
		$oPlaceLookup = new PlaceLookup($oDB);
		$oPlaceLookup->setLanguagePreference($aLangPrefOrder);
		$oPlaceLookup->setIncludeAddressDetails($bShowAddressDetails);
		
		$osm_ids = explode(',', $_GET['osm_ids']);
		
		if ( count($osm_ids) > CONST_Places_Max_ID_count ) 
		{
			userError('Bulk User: Only ' .  CONST_Places_Max_ID_count . " ids are allowed in one request.");
			exit;
		}
		
		$type = ''; 
		$id = 0;
		$aPlaces = array();
		foreach ($osm_ids AS $item) 
		{
			// Skip empty items
			if (empty($item)) continue;
			
			$type = $item[0];
			$id = (int) substr($item, 1);
			if ( $id > 0 && ($type == 'N' || $type == 'W' || $type == 'R') )
			{
				$oPlaceLookup->setOSMID($type, $id);
				$oPlace = $oPlaceLookup->lookup();
				if ($oPlace){
					$aPlaces[] = $oPlace;
				}
			}
		}
	}


	// we want to use the search-* output templates, so we need to convert
	// $aPlaces (the format of reverse search) => $aSearchResults (the format of search)
	$aSearchResults = array();
	foreach ($aPlaces as $oPlace){
		$oResult = $oPlace;
		unset($oResult['aAddress']);
		$oResult['address'] = $oPlace['aAddress'];
		unset($oResult['langaddress']);
		$oResult['name'] = $oPlace['langaddress'];
		// importance score only adds confusiion: the results are ordered exactly as inputted
		// unset($oResult['importance']);
		$aSearchResults[] = $oResult;
	}

	if (CONST_Debug) exit;

	include(CONST_BasePath.'/lib/template/search-'.$sOutputFormat.'.php');

<?php
	@define('CONST_ConnectionBucket_PageType', 'Reverse');
	require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
	require_once(CONST_BasePath.'/lib/log.php');
	require_once(CONST_BasePath.'/lib/PlaceLookup.php');
	require_once(CONST_BasePath.'/lib/PoisNear.php');

	if (strpos(CONST_BulkUserIPs, ','.$_SERVER["REMOTE_ADDR"].',') !== false)
	{
		$fLoadAvg = getLoadAverage();
		if ($fLoadAvg > 2) sleep(60);
		if ($fLoadAvg > 4) sleep(120);
		if ($fLoadAvg > 6)
		{
			echo "Bulk User: Temporary block due to high server load\n";
			exit;
		}
	}

	$oDB =& getDB();
	ini_set('memory_limit', '200M');

	// Format for output
	$sOutputFormat = 'xml';
	if (isset($_GET['format']) && ( $_GET['format'] == 'html' || $_GET['format'] == 'xml' || $_GET['format'] == 'json' || $_GET['format'] == 'jsonv2'))
	{
		$sOutputFormat = $_GET['format'];
	}

	// Preferred language
	$aLangPrefOrder = getPreferredLanguages();
	$hLog = logStart($oDB, 'poisnear', $_SERVER['QUERY_STRING'], $aLangPrefOrder);


	$lat =(float)$_GET['lat'];
	$lon =(float)$_GET['lon'];

	if ((bool)$lat === true && (bool)$lon === true
		&& (isset($_GET['class']) && isset($_GET['type'])) )
	{
		$oPoisNear = new PoisNear($oDB);
		$oPoisNear->setLanguagePreference($aLangPrefOrder);
		$oPoisNear->setLatLon($_GET['lat'], $_GET['lon']);
		$oPoisNear->setClassAndType($_GET['class'], $_GET['type']);
		$aPlaces = $oPoisNear->lookup();
	} else {
		$aPlaces = null;
	}


	if (CONST_Debug)
	{
		var_dump($aPlaces);
		exit;
	}

	$sTileURL = CONST_Map_Tile_URL;
	$sTileAttribution = CONST_Map_Tile_Attribution;
	include(CONST_BasePath.'/lib/template/poisnear-'.$sOutputFormat.'.php');

<?php
	@define('CONST_ConnectionBucket_PageType', 'Reverse');

	require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
	require_once(CONST_BasePath.'/lib/init-website.php');
	require_once(CONST_BasePath.'/lib/log.php');
	require_once(CONST_BasePath.'/lib/PlaceLookup.php');
	require_once(CONST_BasePath.'/lib/ReverseGeocode.php');

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


	$bAsPoints = false;
	$bAsGeoJSON = (boolean)isset($_GET['polygon_geojson']) && $_GET['polygon_geojson'];
	$bAsKML = (boolean)isset($_GET['polygon_kml']) && $_GET['polygon_kml'];
	$bAsSVG = (boolean)isset($_GET['polygon_svg']) && $_GET['polygon_svg'];
	$bAsText = (boolean)isset($_GET['polygon_text']) && $_GET['polygon_text'];
	if ( ( ($bAsGeoJSON?1:0)
			 + ($bAsKML?1:0)
			 + ($bAsSVG?1:0)
			 + ($bAsText?1:0)
			 + ($bAsPoints?1:0)
			 ) > CONST_PolygonOutput_MaximumTypes)
	{
		if (CONST_PolygonOutput_MaximumTypes)
		{
			userError("Select only ".CONST_PolygonOutput_MaximumTypes." polgyon output option");
		}
		else
		{
			userError("Polygon output is disabled");
		}
		exit;
	}


	// Polygon simplification threshold (optional)
	$fThreshold = 0.0;
	if (isset($_GET['polygon_threshold'])) $fThreshold = (float)$_GET['polygon_threshold'];


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

	$hLog = logStart($oDB, 'reverse', $_SERVER['QUERY_STRING'], $aLangPrefOrder);


	if (isset($_GET['osm_type']) && isset($_GET['osm_id']) && (int)$_GET['osm_id'] && ($_GET['osm_type'] == 'N' || $_GET['osm_type'] == 'W' || $_GET['osm_type'] == 'R'))
	{
		$aLookup = array('osm_type' => $_GET['osm_type'], 'osm_id' => $_GET['osm_id']);
	}
	else if (isset($_GET['lat']) && isset($_GET['lon']) && preg_match('/^[+-]?[0-9]*\.?[0-9]+$/', $_GET['lat']) && preg_match('/^[+-]?[0-9]*\.?[0-9]+$/', $_GET['lon']))
	{
		$oReverseGeocode = new ReverseGeocode($oDB);
		$oReverseGeocode->setLanguagePreference($aLangPrefOrder);

		$oReverseGeocode->setLatLon($_GET['lat'], $_GET['lon']);
		$oReverseGeocode->setZoom(@$_GET['zoom']);

		$aLookup = $oReverseGeocode->lookup();
		if (CONST_Debug) var_dump($aLookup);
	}
	else
	{
		$aLookup = null;
	}

	if ($aLookup)
	{
		$oPlaceLookup = new PlaceLookup($oDB);
		$oPlaceLookup->setLanguagePreference($aLangPrefOrder);
		$oPlaceLookup->setIncludeAddressDetails(getParamBool('addressdetails', true));
		$oPlaceLookup->setIncludeExtraTags(getParamBool('extratags', false));
		$oPlaceLookup->setIncludeNameDetails(getParamBool('namedetails', false));

		$aPlace = $oPlaceLookup->lookupPlace($aLookup);

		$oPlaceLookup->setIncludePolygonAsPoints($bAsPoints);
		$oPlaceLookup->setIncludePolygonAsText($bAsText);
		$oPlaceLookup->setIncludePolygonAsGeoJSON($bAsGeoJSON);
		$oPlaceLookup->setIncludePolygonAsKML($bAsKML);
		$oPlaceLookup->setIncludePolygonAsSVG($bAsSVG);
		$oPlaceLookup->setPolygonSimplificationThreshold($fThreshold);

		$fRadius = $fDiameter = getResultDiameter($aPlace);
		$aOutlineResult = $oPlaceLookup->getOutlines($aPlace['place_id'],$aPlace['lon'],$aPlace['lat'],$fRadius);

		$aPlace = array_merge($aPlace, $aOutlineResult);
	}
	else
	{
		$aPlace = null;
	}


	if (CONST_Debug)
	{
		var_dump($aPlace);
		exit;
	}

	if ($sOutputFormat=='html')
	{
		$sDataDate = $oDB->getOne("select TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1");
		$sTileURL = CONST_Map_Tile_URL;
		$sTileAttribution = CONST_Map_Tile_Attribution;
	}
	include(CONST_BasePath.'/lib/template/address-'.$sOutputFormat.'.php');

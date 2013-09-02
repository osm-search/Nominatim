<?php
	@define('CONST_ConnectionBucket_PageType', 'Search');

	require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
	require_once(CONST_BasePath.'/lib/log.php');
        require_once(CONST_BasePath.'/lib/Geocode.php');

	ini_set('memory_limit', '200M');

	$oDB =& getDB();

	// Display defaults
	$fLat = CONST_Default_Lat;
	$fLon = CONST_Default_Lon;
	$iZoom = CONST_Default_Zoom;
	$sSuggestionURL = false;

	$oGeocode =& new Geocode($oDB);

	$aLangPrefOrder = getPreferredLanguages();
	$oGeocode->setLanguagePreference($aLangPrefOrder);

	function loadParamsToGeocode($oGeocode, $aParams, $bBatch = false)
	{
		if (isset($aParams['addressdetails'])) $oGeocode->setIncludeAddressDetails((bool)$aParams['addressdetails']);
		if (isset($aParams['bounded'])) $oGeocode->setBounded((bool)$aParams['bounded']);
		if (isset($aParams['dedupe'])) $oGeocode->setDedupe((bool)$aParams['dedupe']);

		if (isset($aParams['limit'])) $oGeocode->setLimit((int)$aParams['limit']);
		if (isset($aParams['offset'])) $oGeocode->setOffset((int)$aParams['offset']);

		// List of excluded Place IDs - used for more acurate pageing
		if (isset($aParams['exclude_place_ids']) && $aParams['exclude_place_ids'])
		{
			foreach(explode(',',$aParams['exclude_place_ids']) as $iExcludedPlaceID)
			{
				$iExcludedPlaceID = (int)$iExcludedPlaceID;
				if ($iExcludedPlaceID) $aExcludePlaceIDs[$iExcludedPlaceID] = $iExcludedPlaceID;
			}
			$oGeocode->setExcludedPlaceIds($aExcludePlaceIDs);
		}

		// Only certain ranks of feature
		if (isset($aParams['featureType'])) $oGeocode->setFeatureType($aParams['featureType']);
		if (isset($aParams['featuretype'])) $oGeocode->setFeatureType($aParams['featuretype']);

		// Country code list
		if (isset($aParams['countrycodes']))
		{
			$aCountryCodes = array();
			foreach(explode(',',$aParams['countrycodes']) as $sCountryCode)
			{
				if (preg_match('/^[a-zA-Z][a-zA-Z]$/', $sCountryCode))
				{
					$aCountryCodes[] = strtolower($sCountryCode);
				}
			}
			$oGeocode->setCountryCodesList($aCountryCodes);
		}

		if (isset($aParams['viewboxlbrt']) && $aParams['viewboxlbrt'])
		{
			$aCoOrdinatesLBRT = explode(',',$aParams['viewboxlbrt']);
			$oGeocode->setViewBox($aCoOrdinatesLBRT[0], $aCoOrdinatesLBRT[1], $aCoOrdinatesLBRT[2], $aCoOrdinatesLBRT[3]);
		}
		else if (isset($aParams['viewbox']) && $aParams['viewbox'])
		{
			$aCoOrdinatesLTRB = explode(',',$aParams['viewbox']);
			$oGeocode->setViewBox($aCoOrdinatesLTRB[0], $aCoOrdinatesLTRB[3], $aCoOrdinatesLTRB[2], $aCoOrdinatesLTRB[1]);
		}

		if (isset($aParams['route']) && $aParams['route'] && isset($aParams['routewidth']) && $aParams['routewidth'])
		{
			$aPoints = explode(',',$aParams['route']);
			if (sizeof($aPoints) % 2 != 0)
			{
				userError("Uneven number of points");
				exit;
			}
			$fPrevCoord = false;
			$aRoute = array();
			foreach($aPoints as $i => $fPoint)
			{
				if ($i%2)
				{
					$aRoute[] = array((float)$fPoint, $fPrevCoord);
				}
				else
				{
					$fPrevCoord = (float)$fPoint;
				}
			}
			$oGeocode->setRoute($aRoute);
		}

		// Search query
		$sQuery = (isset($aParams['q'])?trim($aParams['q']):'');
		if (!$sQuery && !$bBatch && isset($_SERVER['PATH_INFO']) && $_SERVER['PATH_INFO'][0] == '/')
		{
			$sQuery = substr($_SERVER['PATH_INFO'], 1);

			// reverse order of '/' separated string
			$aPhrases = explode('/', $sQuery);
			$aPhrases = array_reverse($aPhrases);
			$sQuery = join(', ',$aPhrases);
		}
		if (!$sQuery)
		{
			$oGeocode->setStructuredQuery(@$aParams['amenity'], @$aParams['street'], @$aParams['city'], @$aParams['county'], @$aParams['state'], @$aParams['country'], @$aParams['postalcode']);
		}
		else
		{
			$oGeocode->setQuery($sQuery);
		}

	}

	// Format for output
	$sOutputFormat = 'html';
	if (isset($_GET['format']) && ($_GET['format'] == 'html' || $_GET['format'] == 'xml' || $_GET['format'] == 'json' ||  $_GET['format'] == 'jsonv2'))
	{
		$sOutputFormat = $_GET['format'];
	}

	// Show / use polygons
	if ($sOutputFormat == 'html')
	{
		if (isset($_GET['polygon'])) $oGeocode->setIncludePolygonAsText((bool)$_GET['polygon']);
	}
	else
	{
		$bAsPoints = (boolean)isset($_GET['polygon']) && $_GET['polygon'];
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
		$oGeocode->setIncludePolygonAsPoints($bAsPoints);
		$oGeocode->setIncludePolygonAsText($bAsText);
		$oGeocode->setIncludePolygonAsGeoJSON($bAsGeoJSON);
		$oGeocode->setIncludePolygonAsKML($bAsKML);
		$oGeocode->setIncludePolygonAsSVG($bAsSVG);
	}

	loadParamsToGeocode($oGeocode, $_GET, false);

	if (isset($_GET['batch']))
	{
		$aBatch = json_decode($_GET['batch'], true);
		$aBatchResults = array();
		foreach($aBatch as $aBatchParams)
		{
			$oBatchGeocode = clone $oGeocode;
			loadParamsToGeocode($oBatchGeocode, $aBatchParams, true);
			$aSearchResults = $oBatchGeocode->lookup();
			$aBatchResults[] = $aSearchResults;
		}
		include(CONST_BasePath.'/lib/template/search-batch-json.php');
		exit;
	}

	$hLog = logStart($oDB, 'search', $oGeocode->getQueryString(), $aLangPrefOrder);

	$aSearchResults = $oGeocode->lookup();
	if ($aSearchResults === false) $aSearchResults = array();

	$sDataDate = $oDB->getOne("select TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1");

	logEnd($oDB, $hLog, sizeof($aSearchResults));

	$bAsText = $oGeocode->getIncludePolygonAsText();
	$sQuery = $oGeocode->getQueryString();
	$sViewBox = $oGeocode->getViewBoxString();
	$bShowPolygons = (isset($_GET['polygon']) && $_GET['polygon']);
	$aExcludePlaceIDs = $oGeocode->getExcludedPlaceIDs();

	$sMoreURL = CONST_Website_BaseURL.'search?format='.urlencode($sOutputFormat).'&exclude_place_ids='.join(',',$oGeocode->getExcludedPlaceIDs());
	if (isset($_SERVER["HTTP_ACCEPT_LANGUAGE"])) $sMoreURL .= '&accept-language='.$_SERVER["HTTP_ACCEPT_LANGUAGE"];
	if ($bShowPolygons) $sMoreURL .= '&polygon=1';
	if ($oGeocode->getIncludeAddressDetails()) $sMoreURL .= '&addressdetails=1';
	if ($sViewBox) $sMoreURL .= '&viewbox='.urlencode($sViewBox);
	if (isset($_GET['nearlat']) && isset($_GET['nearlon'])) $sMoreURL .= '&nearlat='.(float)$_GET['nearlat'].'&nearlon='.(float)$_GET['nearlon'];
	$sMoreURL .= '&q='.urlencode($sQuery);

	if (CONST_Debug) exit;

	include(CONST_BasePath.'/lib/template/search-'.$sOutputFormat.'.php');

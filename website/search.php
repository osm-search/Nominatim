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

	if (isset($_GET['addressdetails'])) $oGeocode->setIncludeAddressDetails((bool)$_GET['addressdetails']);
	if (isset($_GET['bounded'])) $oGeocode->setBounded((bool)$_GET['bounded']);
	if (isset($_GET['dedupe'])) $oGeocode->setDedupe((bool)$_GET['dedupe']);

	if (isset($_GET['limit'])) $oGeocode->setLimit((int)$_GET['limit']);
	if (isset($_GET['offset'])) $oGeocode->setOffset((int)$_GET['offset']);

	// Format for output
	$sOutputFormat = 'html';
	if (isset($_GET['format']) && ($_GET['format'] == 'html' || $_GET['format'] == 'xml' || $_GET['format'] == 'json' ||  $_GET['format'] == 'jsonv2'))
	{
		$sOutputFormat = $_GET['format'];
	}

	// Show / use polygons
	if ($sOutputFormat == 'html')
	{
		if (isset($_GET['polygon'])) $oGeocode->setIncludePolygonAsPoints((bool)$_GET['polygon']);
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
		$oGeocode->setIncludePolygonAsText($bAsText);
		$oGeocode->setIncludePolygonAsGeoJSON($bAsGeoJSON);
		$oGeocode->setIncludePolygonAsKML($bAsKML);
		$oGeocode->setIncludePolygonAsSVG($bAsSVG);
	}

	// List of excluded Place IDs - used for more acurate pageing
	if (isset($_GET['exclude_place_ids']) && $_GET['exclude_place_ids'])
	{
		foreach(explode(',',$_GET['exclude_place_ids']) as $iExcludedPlaceID)
		{
			$iExcludedPlaceID = (int)$iExcludedPlaceID;
			if ($iExcludedPlaceID) $aExcludePlaceIDs[$iExcludedPlaceID] = $iExcludedPlaceID;
		}
		$oGeocode->setExcludedPlaceIds($aExcludePlaceIDs);
	}

	// Only certain ranks of feature
	if (isset($_GET['featureType'])) $oGeocode->setFeatureType($_GET['featureType']);
	if (isset($_GET['featuretype'])) $oGeocode->setFeatureType($_GET['featuretype']);

	// Country code list
	if (isset($_GET['countrycodes']))
	{
		$aCountryCodes = array();
		foreach(explode(',',$_GET['countrycodes']) as $sCountryCode)
		{
			if (preg_match('/^[a-zA-Z][a-zA-Z]$/', $sCountryCode))
			{
				$aCountryCodes[] = strtolower($sCountryCode);
			}
		}
		$oGeocode->setCountryCodeList($aCountryCodes);
	}

	if (isset($_GET['viewboxlbrt']) && $_GET['viewboxlbrt'])
	{
		$aCoOrdinatesLBRT = explode(',',$_GET['viewboxlbrt']);
		$oGeocode->setViewBox($aCoOrdinatesLBRT[0], $aCoOrdinatesLBRT[1], $aCoOrdinatesLBRT[2], $aCoOrdinatesLBRT[3]);
	}

	if (isset($_GET['viewbox']) && $_GET['viewbox'])
	{
		$aCoOrdinatesLTRB = explode(',',$_GET['viewbox']);
		$oGeocode->setViewBox($aCoOrdinatesLTRB[0], $aCoOrdinatesLTRB[3], $aCoOrdinatesLTRB[2], $aCoOrdinatesLTRB[1]);
	}

	if (isset($_GET['route']) && $_GET['route'] && isset($_GET['routewidth']) && $_GET['routewidth'])
	{
		$aPoints = explode(',',$_GET['route']);
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
	$sQuery = (isset($_GET['q'])?trim($_GET['q']):'');
	if (!$sQuery && isset($_SERVER['PATH_INFO']) && $_SERVER['PATH_INFO'][0] == '/')
	{
		$sQuery = substr($_SERVER['PATH_INFO'], 1);

		// reverse order of '/' separated string
		$aPhrases = explode('/', $sQuery);
		$aPhrases = array_reverse($aPhrases);
		$sQuery = join(', ',$aPhrases);
	}
	if (!$sQuery)
	{
		$oGeocode->setStructuredQuery(@$_GET['amenity'], @$_GET['street'], @$_GET['city'], @$_GET['county'], @$_GET['state'], @$_GET['country'], @$_GET['postalcode']);
	}
	else
	{
		$oGeocode->setQuery($sQuery);
	}

	$hLog = logStart($oDB, 'search', $sQuery, $aLangPrefOrder);

	if (isset($_GET['batch']))
	{
		$aBatch = json_decode($_GET['batch'], true);
		foreach($aBatch as $aItem) {
			var_dump($aItem);
		}
		exit;
	}

	$aSearchResults = $oGeocode->lookup();
	if ($aSearchResults === false) $aSearchResults = array();

	$sDataDate = $oDB->getOne("select TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1");

	logEnd($oDB, $hLog, sizeof($aSearchResults));

	$bAsText = $oGeocode->getIncludePolygonAsText();
	$sQuery = $oGeocode->getQueryString();

	$sMoreURL = CONST_Website_BaseURL.'search?format='.urlencode($sOutputFormat).'&exclude_place_ids='.join(',',$oGeocode->getExcludedPlaceIDs());
	if (isset($_SERVER["HTTP_ACCEPT_LANGUAGE"])) $sMoreURL .= '&accept-language='.$_SERVER["HTTP_ACCEPT_LANGUAGE"];
	if ($oGeocode->getIncludePolygonAsPoints()) $sMoreURL .= '&polygon=1';
	if ($oGeocode->getIncludeAddressDetails()) $sMoreURL .= '&addressdetails=1';
	if (isset($_GET['viewbox']) && $_GET['viewbox']) $sMoreURL .= '&viewbox='.urlencode($_GET['viewbox']);
	if (isset($_GET['nearlat']) && isset($_GET['nearlon'])) $sMoreURL .= '&nearlat='.(float)$_GET['nearlat'].'&nearlon='.(float)$_GET['nearlon'];
	$sMoreURL .= '&q='.urlencode($sQuery);

	if (CONST_Debug) exit;

	include(CONST_BasePath.'/lib/template/search-'.$sOutputFormat.'.php');

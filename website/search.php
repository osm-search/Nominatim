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

	if (isset($aLangPrefOrder['name:de'])) $oGeocode->setReverseInPlan(true);
	if (isset($aLangPrefOrder['name:ru'])) $oGeocode->setReverseInPlan(true);
	if (isset($aLangPrefOrder['name:ja'])) $oGeocode->setReverseInPlan(true);
	if (isset($aLangPrefOrder['name:pl'])) $oGeocode->setReverseInPlan(true);

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

	// Polygon simplification threshold (optional)
	$fThreshold = 0.0;
	if (isset($_GET['polygon_threshold'])) $fThreshold = (float)$_GET['polygon_threshold'];
	$oGeocode->setPolygonSimplificationThreshold($fThreshold);

	$oGeocode->loadParamArray($_GET);

	if (CONST_Search_BatchMode && isset($_GET['batch']))
	{
		$aBatch = json_decode($_GET['batch'], true);
		$aBatchResults = array();
		foreach($aBatch as $aBatchParams)
		{
			$oBatchGeocode = clone $oGeocode;
			$oBatchGeocode->loadParamArray($aBatchParams);
			$oBatchGeocode->setQueryFromParams($aBatchParams);
			$aSearchResults = $oBatchGeocode->lookup();
			$aBatchResults[] = $aSearchResults;
		}
		include(CONST_BasePath.'/lib/template/search-batch-json.php');
		exit;
	} else {
        if (!(isset($_GET['q']) && $_GET['q']) && isset($_SERVER['PATH_INFO']) && $_SERVER['PATH_INFO'][0] == '/')
        {
            $sQuery = substr(rawurldecode($_SERVER['PATH_INFO']), 1);

            // reverse order of '/' separated string
            $aPhrases = explode('/', $sQuery);
            $aPhrases = array_reverse($aPhrases);
            $sQuery = join(', ',$aPhrases);
            $oGeocode->setQuery($sQuery);
        }
        else
        {
            $oGeocode->setQueryFromParams($_GET);
        }

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

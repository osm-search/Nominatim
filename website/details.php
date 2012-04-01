<?php
        require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
        require_once(CONST_BasePath.'/lib/log.php');

	$sOutputFormat = 'html';
/*
        $fLoadAvg = getLoadAverage();
        if ($fLoadAvg > 3)
        {
		echo "Page temporarily blocked due to high server load\n";
                exit;
        }
*/
	ini_set('memory_limit', '200M');

	$oDB =& getDB();

	if (isset($_GET['osmtype']) && isset($_GET['osmid']) && (int)$_GET['osmid'] && ($_GET['osmtype'] == 'N' || $_GET['osmtype'] == 'W' || $_GET['osmtype'] == 'R'))
	{
		$_GET['place_id'] = $oDB->getOne("select place_id from placex where osm_type = '".$_GET['osmtype']."' and osm_id = ".(int)$_GET['osmid']." order by type = 'postcode' asc");
	}

	if (!isset($_GET['place_id']))
	{
		echo "Please select a place id";
		exit;
	}

	$iPlaceID = (int)$_GET['place_id'];

	$iParentPlaceID = $oDB->getOne('select parent_place_id from location_property_tiger where place_id = '.$iPlaceID);
	if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
	$iParentPlaceID = $oDB->getOne('select parent_place_id from location_property_aux where place_id = '.$iPlaceID);
	if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;

	$aLangPrefOrder = getPrefferedLangauges();
	$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted",$aLangPrefOrder))."]";

	$hLog = logStart($oDB, 'details', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

	// Make sure the point we are reporting on is fully indexed
	//$sSQL = "UPDATE placex set indexed = true where indexed = false and place_id = $iPlaceID";
	//$oDB->query($sSQL);

	// Get the details for this point
	$sSQL = "select place_id, osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, importance,";
	$sSQL .= " parent_place_id, rank_address, rank_search, get_searchrank_label(rank_search) as rank_search_label, get_name_by_language(name,$sLanguagePrefArraySQL) as localname, ";
	$sSQL .= " ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea,ST_GeometryType(geometry) as geotype, ST_Y(ST_Centroid(geometry)) as lat,ST_X(ST_Centroid(geometry)) as lon ";
	$sSQL .= " from placex where place_id = $iPlaceID";
	$aPointDetails = $oDB->getRow($sSQL);
	if (PEAR::IsError($aPointDetails))
	{
		failInternalError("Could not get details of place object.", $sSQL, $aPointDetails);
	}

        $aPointDetails['localname'] = $aPointDetails['localname']?$aPointDetails['localname']:$aPointDetails['housenumber'];
	$fLon = $aPointDetails['lon'];
	$fLat = $aPointDetails['lat'];
	$iZoom = 14;

	$aClassType = getClassTypesWithImportance();
	$aPointDetails['icon'] = $aClassType[$aPointDetails['class'].':'.$aPointDetails['type']]['icon'];

	// Get all alternative names (languages, etc)
	$sSQL = "select (each(name)).key,(each(name)).value from placex where place_id = $iPlaceID order by (each(name)).key";
	$aPointDetails['aNames'] = $oDB->getAssoc($sSQL);

	// Extra tags
	$sSQL = "select (each(extratags)).key,(each(extratags)).value from placex where place_id = $iPlaceID order by (each(extratags)).key";
	$aPointDetails['aExtraTags'] = $oDB->getAssoc($sSQL);

	// Get the bounding box and outline polygon
	$sSQL = "select ST_AsText(geometry) as outlinestring,";
	$sSQL .= "ST_YMin(geometry) as minlat,ST_YMax(geometry) as maxlat,";
	$sSQL .= "ST_XMin(geometry) as minlon,ST_XMax(geometry) as maxlon";
	$sSQL .= " from placex where place_id = $iPlaceID";
	$aPointPolygon = $oDB->getRow($sSQL);
	IF (PEAR::IsError($aPointPolygon))
	{
		failInternalError("Could not get bounding box of place object.", $sSQL, $aPointPolygon);
	}
	if (preg_match('#POLYGON\\(\\(([- 0-9.,]+)#',$aPointPolygon['outlinestring'],$aMatch))
	{
		preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/',$aMatch[1],$aPolyPoints,PREG_SET_ORDER);
	}
	elseif (preg_match('#MULTIPOLYGON\\(\\(\\(([- 0-9.,]+)#',$aPointPolygon['outlinestring'],$aMatch))
	{
		// TODO: this just takes the first ring
		preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/',$aMatch[1],$aPolyPoints,PREG_SET_ORDER);
	}
	elseif (preg_match('#POINT\\((-?[0-9.]+) (-?[0-9.]+)\\)#',$aPointPolygon['outlinestring'],$aMatch))
	{
		$fRadius = 0.01;
		if ($aPointDetails['rank_search'] > 20) $fRadius = 0.0001;
		$iSteps = min(max(($fRadius * 40000)^2,16),100);
		$fStepSize = (2*pi())/$iSteps;
		$aPolyPoints = array();
		for($f = 0; $f < 2*pi(); $f += $fStepSize)
		{

			$aPolyPoints[] = array('',$aMatch[1]+($fRadius*sin($f)),$aMatch[2]+($fRadius*cos($f)));
		}
		$aPointPolygon['minlat'] = $aPointPolygon['minlat'] - $fRadius;
		$aPointPolygon['maxlat'] = $aPointPolygon['maxlat'] + $fRadius;
		$aPointPolygon['minlon'] = $aPointPolygon['minlon'] - $fRadius;
		$aPointPolygon['maxlon'] = $aPointPolygon['maxlon'] + $fRadius;
	}

	// Address
	$aAddressLines = getAddressDetails($oDB, $sLanguagePrefArraySQL, $iPlaceID, $aPointDetails['country_code'], true);

	// Linked places
	$sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, st_distance(geometry, placegeometry) as distance, ";
	$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
	$sSQL .= " from placex, (select geometry as placegeometry from placex where place_id = $iPlaceID) as x";
	$sSQL .= " where linked_place_id = $iPlaceID";
	$sSQL .= " order by rank_address asc,rank_search asc,get_name_by_language(name,$sLanguagePrefArraySQL),housenumber";
	$aLinkedLines = $oDB->getAll($sSQL);

	// All places this is an imediate parent of
	$sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, st_distance(geometry, placegeometry) as distance, ";
	$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
	$sSQL .= " from placex, (select geometry as placegeometry from placex where place_id = $iPlaceID) as x";
	$sSQL .= " where parent_place_id = $iPlaceID";
	$sSQL .= " order by rank_address asc,rank_search asc,get_name_by_language(name,$sLanguagePrefArraySQL),housenumber";
	$aParentOfLines = $oDB->getAll($sSQL);

	$aPlaceSearchNameKeywords = false;
	$aPlaceSearchAddressKeywords = false;
	if (isset($_GET['keywords']) && $_GET['keywords'])
	{
		$sSQL = "select * from search_name where place_id = $iPlaceID";
		$aPlaceSearchName = $oDB->getRow($sSQL);
		$sSQL = "select * from word where word_id in (".substr($aPlaceSearchName['name_vector'],1,-1).")";
		$aPlaceSearchNameKeywords = $oDB->getAll($sSQL);
		$sSQL = "select * from word where word_id in (".substr($aPlaceSearchName['nameaddress_vector'],1,-1).")";
		$aPlaceSearchAddressKeywords = $oDB->getAll($sSQL);
	}

	logEnd($oDB, $hLog, 1);

	include(CONST_BasePath.'/lib/template/details-'.$sOutputFormat.'.php');

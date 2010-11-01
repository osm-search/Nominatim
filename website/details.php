<?php
        require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
        require_once(CONST_BasePath.'/lib/log.php');

        $fLoadAvg = getLoadAverage();
        if ($fLoadAvg > 3)
        {
		echo "Page temporarily blocked due to high server load\n";
                exit;
        }

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

	$aLangPrefOrder = getPrefferedLangauges();
	$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted",$aLangPrefOrder))."]";

	$hLog = logStart($oDB, 'details', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

	// Make sure the point we are reporting on is fully indexed
	//$sSQL = "UPDATE placex set indexed = true where indexed = false and place_id = $iPlaceID";
	//$oDB->query($sSQL);

	// Get the details for this point
	$sSQL = "select place_id, osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, ";
	$sSQL .= " parent_place_id, rank_address, rank_search, get_searchrank_label(rank_search) as rank_search_label, get_name_by_language(name,$sLanguagePrefArraySQL) as localname, ";
	$sSQL .= " ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea,ST_GeometryType(geometry) as geotype, ST_Y(ST_Centroid(geometry)) as lat,ST_X(ST_Centroid(geometry)) as lon ";
	$sSQL .= " from placex where place_id = $iPlaceID";
	$aPointDetails = $oDB->getRow($sSQL);
	IF (PEAR::IsError($aPointDetails))
	{
		var_dump($aPointDetails);
		exit;
	}
        $aPointDetails['localname'] = $aPointDetails['localname']?$aPointDetails['localname']:$aPointDetails['housenumber'];
	$fLon = $aPointDetails['lon'];
	$fLat = $aPointDetails['lat'];
	$iZoom = 14;

	$aClassType = getClassTypesWithImportance();
	$aPointDetails['icon'] = $aClassType[$aPointDetails['class'].':'.$aPointDetails['type']]['icon'];

	// Get all alternative names (languages, etc)
	$aPointDetails['aNames'] = array();
/*
	for($i = 1; $i <= $aPointDetails['numnames']; $i++)
	{
		$sSQL = "select name[$i].key, name[$i].value from placex where place_id = $iPlaceID limit 1";
		$aNameItem = $oDB->getRow($sSQL);
		if (substr($aNameItem['key'],0,5) == 'name:') $aNameItem['key'] = substr($aNameItem['key'],5);
		$aPointDetails['aNames'][$aNameItem['key']] = $aNameItem['value'];
	}
*/
	// Get the bounding box and outline polygon
	$sSQL = "select *,ST_AsText(outline) as outlinestring from get_place_boundingbox($iPlaceID)";
	$aPointPolygon = $oDB->getRow($sSQL);
	IF (PEAR::IsError($aPointPolygon))
	{
		var_dump($aPointPolygon);
		exit;
	}
	if (preg_match('#POLYGON\\(\\(([- 0-9.,]+)#',$aPointPolygon['outlinestring'],$aMatch))
	{
		preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/',$aMatch[1],$aPolyPoints,PREG_SET_ORDER);
	}
	elseif (preg_match('#POINT\\((-?[0-9.]+) (-?[0-9.]+)\\)#',$aPointPolygon['outlinestring'],$aMatch))
	{
		$fRadius = 0.01;
		$iSteps = ($fRadius * 40000)^2;
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

	// If it is a road then force all nearby buildings to be indexed (so we can show then in the list)
/*
	if ($aPointDetails['rank_address'] == 26)
	{
		$sSQL = "UPDATE placex set indexed = true from placex as srcplace where placex.indexed = false";
		$sSQL .= " and ST_DWithin(placex.geometry, srcplace.geometry, 0.0005) and srcplace.place_id = $iPlaceID";
		$oDB->query($sSQL);
	}
*/
	// Address
	$aAddressLines = getAddressDetails($oDB, $sLanguagePrefArraySQL, $iPlaceID, $aPointDetails['country_code'], true);
/*
	$sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, rank_search, ";
	$sSQL .= "get_searchrank_label(rank_search) as rank_search_label, fromarea, distance, ";
	$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
	$sSQL .= " from place_addressline join placex on (address_place_id = placex.place_id)";
	$sSQL .= " where place_addressline.place_id = $iPlaceID and ((rank_address > 0 AND rank_address < ".$aPointDetails['rank_address'].") OR address_place_id = $iPlaceID) and placex.place_id != $iPlaceID";
	if ($aPointDetails['country_code'])
	{
		$sSQL .= " and (placex.country_code IS NULL OR placex.country_code = '".$aPointDetails['country_code']."' OR rank_address < 4)";
	}
	$sSQL .= " order by cached_rank_address desc,rank_search desc,fromarea desc,distance asc,namelength desc";
	$aAddressLines = $oDB->getAll($sSQL);
	IF (PEAR::IsError($aAddressLines))
	{
		var_dump($aAddressLines);
		exit;
	}
*/
	// All places this is a parent of
	$iMaxRankAddress = $aPointDetails['rank_address']+13;
	$sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, cached_rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, distance, ";
	$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
	$sSQL .= " from (select * from place_addressline where address_place_id = $iPlaceID and cached_rank_address < $iMaxRankAddress) as place_addressline join placex on (place_addressline.place_id = placex.place_id)";
	$sSQL .= " where place_addressline.address_place_id = $iPlaceID and placex.rank_address < $iMaxRankAddress and cached_rank_address > 0 and placex.place_id != $iPlaceID";
	$sSQL .= " and type != 'postcode'";
	$sSQL .= " order by cached_rank_address asc,rank_search asc,get_name_by_language(name,$sLanguagePrefArraySQL),housenumber limit 1000";
	$aParentOfLines = $oDB->getAll($sSQL);

	logEnd($oDB, $hLog, 1);

	include('.htlib/output/details-html.php');

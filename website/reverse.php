<?php
	@define('CONST_ConnectionBucket_PageType', 'Reverse');

	require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
	require_once(CONST_BasePath.'/lib/log.php');

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
        if (isset($_GET['format']) && ($_GET['format'] == 'xml' || $_GET['format'] == 'json' || $_GET['format'] == 'jsonv2'))
        {
                $sOutputFormat = $_GET['format'];
        }

	// Show address breakdown
	$bShowAddressDetails = true;
	if (isset($_GET['addressdetails'])) $bShowAddressDetails = (bool)$_GET['addressdetails'];

        // Preferred language
        $aLangPrefOrder = getPreferredLanguages();
        $sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted",$aLangPrefOrder))."]";

	$hLog = logStart($oDB, 'reverse', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

        if (isset($_GET['osm_type']) && isset($_GET['osm_id']) && (int)$_GET['osm_id'] && ($_GET['osm_type'] == 'N' || $_GET['osm_type'] == 'W' || $_GET['osm_type'] == 'R'))
        {
                $iPlaceID = $oDB->getOne("select place_id from placex where osm_type = '".$_GET['osm_type']."' and osm_id = ".(int)$_GET['osm_id']." order by type = 'postcode' asc");
		if (!$iPlaceID) $sError = 'OSM ID Not Found';
        }
	else
	{
		// Location to look up
		$fLat = (float)$_GET['lat'];
		$fLon = (float)$_GET['lon'];
		$sPointSQL = "ST_SetSRID(ST_Point($fLon,$fLat),4326)";

		// Zoom to rank, this could probably be calculated but a lookup gives fine control
		$aZoomRank = array(
			0 => 2, // Continent / Sea
			1 => 2,
			2 => 2,
			3 => 4, // Country
			4 => 4,
			5 => 8, // State
			6 => 10, // Region
			7 => 10,
			8 => 12, // County
			9 => 12,
			10 => 17, // City
			11 => 17,
			12 => 18, // Town / Village
			13 => 18,
			14 => 22, // Suburb
			15 => 22,
			16 => 26, // Street, TODO: major street?
			17 => 26,
			18 => 30, // or >, Building
			19 => 30, // or >, Building
			);
		$iMaxRank = (isset($_GET['zoom']) && isset($aZoomRank[$_GET['zoom']]))?$aZoomRank[$_GET['zoom']]:28;

		// Find the nearest point
		$fSearchDiam = 0.0001;
		$iPlaceID = null;
		$aArea = false;
		$fMaxAreaDistance = 1;
		while(!$iPlaceID && $fSearchDiam < $fMaxAreaDistance)
		{
			$fSearchDiam = $fSearchDiam * 2;

			// If we have to expand the search area by a large amount then we need a larger feature
			// then there is a limit to how small the feature should be
			if ($fSearchDiam > 2 && $iMaxRank > 4) $iMaxRank = 4;
			if ($fSearchDiam > 1 && $iMaxRank > 9) $iMaxRank = 8;
			if ($fSearchDiam > 0.8 && $iMaxRank > 10) $iMaxRank = 10;
			if ($fSearchDiam > 0.6 && $iMaxRank > 12) $iMaxRank = 12;
			if ($fSearchDiam > 0.2 && $iMaxRank > 17) $iMaxRank = 17;
			if ($fSearchDiam > 0.1 && $iMaxRank > 18) $iMaxRank = 18;
			if ($fSearchDiam > 0.008 && $iMaxRank > 22) $iMaxRank = 22;
			if ($fSearchDiam > 0.001 && $iMaxRank > 26) $iMaxRank = 26;

			$sSQL = 'select place_id,parent_place_id,rank_search from placex';
			$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', geometry, '.$fSearchDiam.')';
			$sSQL .= ' and rank_search != 28 and rank_search >= '.$iMaxRank;
			$sSQL .= ' and (name is not null or housenumber is not null)';
			$sSQL .= ' and class not in (\'waterway\',\'railway\',\'tunnel\',\'bridge\')';
			$sSQL .= ' and (ST_GeometryType(geometry) not in (\'ST_Polygon\',\'ST_MultiPolygon\') ';
			$sSQL .= ' OR ST_DWithin('.$sPointSQL.', ST_Centroid(geometry), '.$fSearchDiam.'))';
			$sSQL .= ' ORDER BY ST_distance('.$sPointSQL.', geometry) ASC limit 1';
//var_dump($sSQL);
			$aPlace = $oDB->getRow($sSQL);
			if (PEAR::IsError($aPlace))
			{
				failInternalError("Could not determine closest place.", $sSQL, $iPlaceID); 
			}
			$iPlaceID = $aPlace['place_id'];
			$iParentPlaceID = $aPlace['parent_place_id'];
		}

		// The point we found might be too small - use the address to find what it is a child of
		if ($iPlaceID && $iMaxRank < 28)
		{
			if ($aPlace['rank_search'] > 28 && $iParentPlaceID) {
				$iPlaceID = $iParentPlaceID;
			}
			$sSQL = "select address_place_id from place_addressline where place_id = $iPlaceID order by abs(cached_rank_address - $iMaxRank) asc,cached_rank_address desc,isaddress desc,distance desc limit 1";
			$iPlaceID = $oDB->getOne($sSQL);
			if (PEAR::IsError($iPlaceID))
			{
				failInternalError("Could not get parent for place.", $sSQL, $iPlaceID); 
			}
			if (!$iPlaceID)
			{
				$iPlaceID = $aPlace['place_id'];
			}
		}
	}

	if ($iPlaceID)
	{
		$sSQL = "select placex.*,";
        	$sSQL .= " get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
	        $sSQL .= " get_name_by_language(name, $sLanguagePrefArraySQL) as placename,";
        	$sSQL .= " get_name_by_language(name, ARRAY['ref']) as ref,";
        	$sSQL .= " st_y(st_centroid(geometry)) as lat, st_x(st_centroid(geometry)) as lon";
	        $sSQL .= " from placex where place_id = $iPlaceID ";
//var_dump($sSQL);
		$aPlace = $oDB->getRow($sSQL);

		if ($bShowAddressDetails)
		{
			$aAddress = getAddressDetails($oDB, $sLanguagePrefArraySQL, $iPlaceID, $aPlace['country_code']);
		}
		$aClassType = getClassTypes();
		$sAddressType = '';
		$sClassType = $aPlace['class'].':'.$aPlace['type'].':'.$aPlace['admin_level'];
		if (isset($aClassType[$sClassType]) && isset($aClassType[$sClassType]['simplelabel']))
		{
			$sAddressType = $aClassType[$aClassType]['simplelabel'];
		}
		else
		{
			$sClassType = $aPlace['class'].':'.$aPlace['type'];
			if (isset($aClassType[$sClassType]) && isset($aClassType[$sClassType]['simplelabel']))
				$sAddressType = $aClassType[$sClassType]['simplelabel'];
			else $sAddressType = $aPlace['class'];
		}
		$aPlace['addresstype'] = $sAddressType;

	}
	include(CONST_BasePath.'/lib/template/address-'.$sOutputFormat.'.php');

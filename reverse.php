<?php

        require_once('.htlib/init.php');

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

        ini_set('memory_limit', '200M');

        // Format for output
	$sOutputFormat = 'xml';
        if (isset($_GET['format']) && ($_GET['format'] == 'xml' || $_GET['format'] == 'json'))
        {
                $sOutputFormat = $_GET['format'];
        }

        // Prefered language
        $aLangPrefOrder = getPrefferedLangauges();
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
			18 => 28, // or >, Building
			19 => 30, // or >, Building
			);
		$iMaxRank = isset($aZoomRank[$_GET['zoom']])?$aZoomRank[$_GET['zoom']]:28;

		// Find the nearest point
		$fSearchDiam = 0.0001;
		$iPlaceID = null;
		$aArea = false;
		$fMaxAreaDistance = 10;
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
			if ($fSearchDiam > 0.01 && $iMaxRank > 22) $iMaxRank = 22;

			if ($iMaxRank >= 26)
			{
				// Street level search is done using placex table
				$sSQL = 'select place_id from placex';
				$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', geometry, '.$fSearchDiam.')';
				$sSQL .= ' and rank_search >= 26 and rank_search <= '.$iMaxRank;
				$sSQL .= ' and (ST_GeometryType(geometry) not in (\'ST_Polygon\',\'ST_MultiPolygon\') ';
				$sSQL .= ' OR ST_DWithin('.$sPointSQL.', ST_Centroid(geometry), '.$fSearchDiam.'))';
				$sSQL .= ' ORDER BY rank_search desc, ST_distance('.$sPointSQL.', geometry) ASC limit 1';
				$iPlaceID = $oDB->getOne($sSQL);
				if (PEAR::IsError($iPlaceID))
				{
					var_Dump($sSQL, $iPlaceID); 
					exit;
				}
			}
			else
			{
				// Other search uses the location_point and location_area tables

				// If we've not yet done the area search do it now
				if ($aArea === false)
				{
					$sSQL = 'select place_id,rank_address,ST_distance('.$sPointSQL.', centroid) as distance from location_area';
					$sSQL .= ' WHERE ST_Contains(area,'.$sPointSQL.') and rank_search <= '.$iMaxRank;
					$sSQL .= ' ORDER BY rank_address desc, ST_distance('.$sPointSQL.', centroid) ASC limit 1';
					$aArea = $oDB->getRow($sSQL);
					if ($aArea) $fMaxAreaDistance = $aArea['distance'];
				}

				// Different search depending if we found an area match
				if ($aArea)
				{
					// Found best match area - is there a better point match?
					$sSQL = 'select place_id from location_point_'.($iMaxRank+1);
					$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', centroid, '.$fSearchDiam.') ';
					$sSQL .= ' and rank_search > '.($aArea['rank_address']+3);
					$sSQL .= ' ORDER BY rank_address desc, ST_distance('.$sPointSQL.', centroid) ASC limit 1';
					$iPlaceID = $oDB->getOne($sSQL);
					if (PEAR::IsError($iPlaceID))
					{
						var_Dump($sSQL, $iPlaceID); 
						exit;
					}
				}
				else
				{
					$sSQL = 'select place_id from location_point_'.($iMaxRank+1);
					$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', centroid, '.$fSearchDiam.') ';
					$sSQL .= ' ORDER BY rank_address desc, ST_distance('.$sPointSQL.', centroid) ASC limit 1';
					$iPlaceID = $oDB->getOne($sSQL);
					if (PEAR::IsError($iPlaceID))
					{
						var_Dump($sSQL, $iPlaceID); 
						exit;
					}
				}
			}
		}
		if (!$iPlaceID && $aArea) $iPlaceID = $aArea['place_id'];
	}

	if ($iPlaceID)
	{
		$sSQL = "select placex.*,";
        	$sSQL .= " get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
	        $sSQL .= " get_name_by_language(name, $sLanguagePrefArraySQL) as placename,";
        	$sSQL .= " get_name_by_language(name, ARRAY['ref']) as ref";
	        $sSQL .= " from placex where place_id = $iPlaceID ";
		$aPlace = $oDB->getRow($sSQL);

		$aAddress = getAddressDetails($oDB, $sLanguagePrefArraySQL, $iPlaceID, $aPlace['country_code']);
	}
	include('.htlib/output/address-'.$sOutputFormat.'.php');

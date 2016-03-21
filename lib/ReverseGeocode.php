<?php
	class ReverseGeocode
	{
		protected $oDB;

		protected $fLat;
		protected $fLon;
		protected $iMaxRank = 28;

		protected $aLangPrefOrder = array();

		function ReverseGeocode(&$oDB)
		{
			$this->oDB =& $oDB;
		}

		function setLanguagePreference($aLangPref)
		{
			$this->aLangPrefOrder = $aLangPref;
		}

		function setLatLon($fLat, $fLon)
		{
			$this->fLat = (float)$fLat;
			$this->fLon = (float)$fLon;
		}

		function setRank($iRank)
		{
			$this->iMaxRank = $iRank;
		}

		function setZoom($iZoom)
		{
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
			$this->iMaxRank = (isset($iZoom) && isset($aZoomRank[$iZoom]))?$aZoomRank[$iZoom]:28;
		}

		function lookup()
		{
			$sPointSQL = 'ST_SetSRID(ST_Point('.$this->fLon.','.$this->fLat.'),4326)';
			$iMaxRank = $this->iMaxRank;
			$iMaxRank_orig = $this->iMaxRank;

			// Find the nearest point
			$fSearchDiam = 0.0004;
			$iPlaceID = null;
			$aArea = false;
			$fMaxAreaDistance = 1;
			$bIsInUnitedStates = false;
			$bPlaceIsTiger = false;
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

				$sSQL = 'select place_id,parent_place_id,rank_search,calculated_country_code from placex';
				$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', geometry, '.$fSearchDiam.')';
				$sSQL .= ' and rank_search != 28 and rank_search >= '.$iMaxRank;
				$sSQL .= ' and (name is not null or housenumber is not null)';
				$sSQL .= ' and class not in (\'waterway\',\'railway\',\'tunnel\',\'bridge\',\'man_made\')';
				$sSQL .= ' and indexed_status = 0 ';
				$sSQL .= ' and (ST_GeometryType(geometry) not in (\'ST_Polygon\',\'ST_MultiPolygon\') ';
				$sSQL .= ' OR ST_DWithin('.$sPointSQL.', centroid, '.$fSearchDiam.'))';
				$sSQL .= ' ORDER BY ST_distance('.$sPointSQL.', geometry) ASC limit 1';
				if (CONST_Debug) var_dump($sSQL);
				$aPlace = $this->oDB->getRow($sSQL);
				if (PEAR::IsError($aPlace))
				{
					failInternalError("Could not determine closest place.", $sSQL, $aPlace);
				}
				$iPlaceID = $aPlace['place_id'];
				$iParentPlaceID = $aPlace['parent_place_id'];
				$bIsInUnitedStates = ($aPlace['calculated_country_code'] == 'us');
			}

			// Only street found? If it's in the US we can check TIGER data for nearest housenumber
			if ($bIsInUnitedStates && $iMaxRank_orig >= 28 && $iPlaceID && ($aPlace['rank_search'] == 26 || $aPlace['rank_search'] == 27 ))
			{
				$fSearchDiam = 0.001;
				$sSQL = 'SELECT place_id,parent_place_id,30 as rank_search, ST_line_locate_point(linegeo,'.$sPointSQL.') as fraction';
				//if (CONST_Debug) { $sSQL .= ', housenumber, ST_distance('.$sPointSQL.', centroid) as distance, st_y(centroid) as lat, st_x(centroid) as lon'; }
				$sSQL .= ' FROM location_property_tiger WHERE parent_place_id = '.$iPlaceID;
				$sSQL .= ' AND ST_DWithin('.$sPointSQL.', linegeo, '.$fSearchDiam.')';  //no centroid anymore in Tiger data, now we have lines
				$sSQL .= ' ORDER BY ST_distance('.$sPointSQL.', linegeo) ASC limit 1';


				// print all house numbers in the parent (street)
				/*if (CONST_Debug)
				{
					$sSQL = preg_replace('/limit 1/', 'limit 100', $sSQL);
					var_dump($sSQL);

					$aAllHouses = $this->oDB->getAll($sSQL);
					foreach($aAllHouses as $i)
					{
						echo $i['housenumber'] . ' | ' . $i['distance'] * 1000 . ' | ' . $i['lat'] . ' | ' . $i['lon']. ' | '. "<br>\n";
					}
				}*/

				$aPlaceTiger = $this->oDB->getRow($sSQL);
				if (PEAR::IsError($aPlace))
				{
					failInternalError("Could not determine closest Tiger place.", $sSQL, $aPlaceTiger);
				}
				if ($aPlaceTiger)
				{
					if (CONST_Debug) var_dump('found Tiger place', $aPlaceTiger);
					$bPlaceIsTiger = true;
					$aPlace = $aPlaceTiger;
					$iPlaceID = $aPlaceTiger['place_id'];
					$iParentPlaceID = $aPlaceTiger['parent_place_id']; // the street
					$iFraction = $aPlaceTiger['fraction'];
				}
			}

			// The point we found might be too small - use the address to find what it is a child of
			if ($iPlaceID && $iMaxRank < 28)
			{
				if ($aPlace['rank_search'] > 28 && $iParentPlaceID && !$bPlaceIsTiger)
				{
					$iPlaceID = $iParentPlaceID;
				}
				$sSQL = "select address_place_id from place_addressline where place_id = $iPlaceID order by abs(cached_rank_address - $iMaxRank) asc,cached_rank_address desc,isaddress desc,distance desc limit 1";
				$iPlaceID = $this->oDB->getOne($sSQL);
				if (PEAR::IsError($iPlaceID))
				{
					failInternalError("Could not get parent for place.", $sSQL, $iPlaceID);
				}
				if (!$iPlaceID)
				{
					$iPlaceID = $aPlace['place_id'];
				}
			}

			return array('place_id' => $iPlaceID,
						 'type' => $bPlaceIsTiger ? 'tiger' : 'osm',
						 'fraction' => $bPlaceIsTiger ? $iFraction : -1 );
		}
	}
?>

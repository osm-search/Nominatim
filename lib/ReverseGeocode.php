<?php

class ReverseGeocode
{
	protected $oDB;
	protected $iMaxRank = 28;

	function ReverseGeocode(&$oDB)
	{
		$this->oDB =& $oDB;
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

	// returns { place_id =>, type => '(osm|tiger)' }
	// fails if no place was found
	function lookup($fLat, $fLon, $bDoInterpolation = true)
	{
		$sPointSQL = 'ST_SetSRID(ST_Point('.$fLon.','.$fLat.'),4326)';
		$iMaxRank = $this->iMaxRank;

		// Find the nearest point
		$fSearchDiam = 0.0004;
		$iPlaceID = null;
		$aArea = false;
		$fMaxAreaDistance = 1;
		$bIsInUnitedStates = false;
		$bPlaceIsTiger = false;
		$bPlaceIsLine = false;
		while (!$iPlaceID && $fSearchDiam < $fMaxAreaDistance) {
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

			$sSQL = 'select place_id,parent_place_id,rank_search,calculated_country_code';
			$sSQL .= ' FROM placex';
			$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', geometry, '.$fSearchDiam.')';
			$sSQL .= ' and rank_search != 28 and rank_search >= '.$iMaxRank;
			$sSQL .= ' and (name is not null or housenumber is not null)';
			$sSQL .= ' and class not in (\'waterway\',\'railway\',\'tunnel\',\'bridge\',\'man_made\')';
			$sSQL .= ' and indexed_status = 0 ';
			$sSQL .= ' and (ST_GeometryType(geometry) not in (\'ST_Polygon\',\'ST_MultiPolygon\') ';
			$sSQL .= ' OR ST_DWithin('.$sPointSQL.', centroid, '.$fSearchDiam.'))';
			$sSQL .= ' ORDER BY ST_distance('.$sPointSQL.', geometry) ASC limit 1';
			if (CONST_Debug) var_dump($sSQL);
			$aPlace = chksql($this->oDB->getRow($sSQL), "Could not determine closest place.");
			$iPlaceID = $aPlace['place_id'];
			$iParentPlaceID = $aPlace['parent_place_id'];
			$bIsInUnitedStates = ($aPlace['calculated_country_code'] == 'us');
		}

		// if a street or house was found, look in interpolation lines table
		if ($bDoInterpolation && $this->iMaxRank >= 28 && $aPlace && $aPlace['rank_search'] >= 26) {
			// if a house was found, search the interpolation line that is at least as close as the house
			$sSQL = 'SELECT place_id, parent_place_id, 30 as rank_search, ST_line_locate_point(linegeo,'.$sPointSQL.') as fraction';
			$sSQL .= ' FROM location_property_osmline';
			$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', linegeo, '.$fSearchDiam.')';
			$sSQL .= ' and indexed_status = 0 ';
			$sSQL .= ' ORDER BY ST_distance('.$sPointSQL.', linegeo) ASC limit 1';
			
			if (CONST_Debug) {
				$sSQL = preg_replace('/limit 1/', 'limit 100', $sSQL);
				var_dump($sSQL);

				$aAllHouses = chksql($this->oDB->getAll($sSQL));
				foreach ($aAllHouses as $i) {
					echo $i['housenumber'] . ' | ' . $i['distance'] * 1000 . ' | ' . $i['lat'] . ' | ' . $i['lon']. ' | '. "<br>\n";
				}
			}
			$aPlaceLine = chksql(
				$this->oDB->getRow($sSQL),
				"Could not determine closest housenumber on an osm interpolation line."
			);

			if ($aPlaceLine) {
				if (CONST_Debug) var_dump('found housenumber in interpolation lines table', $aPlaceLine);
				if ($aPlace['rank_search'] == 30) {
					// if a house was already found in placex, we have to find out,
					// if the placex house or the interpolated house are closer to the searched point
					// distance between point and placex house
					$sSQL = 'SELECT ST_distance('.$sPointSQL.', house.geometry) as distance FROM placex as house WHERE house.place_id='.$iPlaceID;
					$aDistancePlacex = chksql(
						$this->oDB->getRow($sSQL),
						"Could not determine distance between searched point and placex house."
					);
					$fDistancePlacex = $aDistancePlacex['distance'];
					// distance between point and interpolated house (fraction on interpolation line)
					$sSQL = 'SELECT ST_distance('.$sPointSQL.', ST_LineInterpolatePoint(linegeo, '.$aPlaceLine['fraction'].')) as distance';
					$sSQL .= ' FROM location_property_osmline WHERE place_id = '.$aPlaceLine['place_id'];
					$aDistanceInterpolation = chksql(
						$this->oDB->getRow($sSQL),
						"Could not determine distance between searched point and interpolated house."
					);
					$fDistanceInterpolation = $aDistanceInterpolation['distance'];
					if ($fDistanceInterpolation < $fDistancePlacex) {
						// interpolation is closer to point than placex house
						$bPlaceIsLine = true;
						$aPlace = $aPlaceLine;
						$iPlaceID = $aPlaceLine['place_id'];
						$iParentPlaceID = $aPlaceLine['parent_place_id']; // the street
						$fFraction = $aPlaceLine['fraction'];
						$iMaxRank = 30;
					}
					// else: nothing to do, take placex house from above
				} else {
					$bPlaceIsLine = true;
					$aPlace = $aPlaceLine;
					$iPlaceID = $aPlaceLine['place_id'];
					$iParentPlaceID = $aPlaceLine['parent_place_id']; // the street
					$fFraction = $aPlaceLine['fraction'];
					$iMaxRank = 30;
				}
			}
		}
		
		// Only street found? If it's in the US we can check TIGER data for nearest housenumber
		if (CONST_Use_US_Tiger_Data && $bDoInterpolation && $bIsInUnitedStates && $this->iMaxRank >= 28 && $iPlaceID && ($aPlace['rank_search'] == 26 || $aPlace['rank_search'] == 27 )) {
			$fSearchDiam = 0.001;
			$sSQL = 'SELECT place_id,parent_place_id,30 as rank_search, ST_line_locate_point(linegeo,'.$sPointSQL.') as fraction';
			//if (CONST_Debug) { $sSQL .= ', housenumber, ST_distance('.$sPointSQL.', centroid) as distance, st_y(centroid) as lat, st_x(centroid) as lon'; }
			$sSQL .= ' FROM location_property_tiger WHERE parent_place_id = '.$iPlaceID;
			$sSQL .= ' AND ST_DWithin('.$sPointSQL.', linegeo, '.$fSearchDiam.')';  //no centroid anymore in Tiger data, now we have lines
			$sSQL .= ' ORDER BY ST_distance('.$sPointSQL.', linegeo) ASC limit 1';

			if (CONST_Debug) {
				$sSQL = preg_replace('/limit 1/', 'limit 100', $sSQL);
				var_dump($sSQL);

				$aAllHouses = chksql($this->oDB->getAll($sSQL));
				foreach ($aAllHouses as $i) {
					echo $i['housenumber'] . ' | ' . $i['distance'] * 1000 . ' | ' . $i['lat'] . ' | ' . $i['lon']. ' | '. "<br>\n";
				}
			}

			$aPlaceTiger = chksql($this->oDB->getRow($sSQL), "Could not determine closest Tiger place.");
			if ($aPlaceTiger) {
				if (CONST_Debug) var_dump('found Tiger housenumber', $aPlaceTiger);
				$bPlaceIsTiger = true;
				$aPlace = $aPlaceTiger;
				$iPlaceID = $aPlaceTiger['place_id'];
				$iParentPlaceID = $aPlaceTiger['parent_place_id']; // the street
				$fFraction = $aPlaceTiger['fraction'];
				$iMaxRank = 30;
			}
		}

		// The point we found might be too small - use the address to find what it is a child of
		if ($iPlaceID && $iMaxRank < 28) {
			if (($aPlace['rank_search'] > 28 || $bPlaceIsTiger || $bPlaceIsLine) && $iParentPlaceID) {
				$iPlaceID = $iParentPlaceID;
			}
			$sSQL  = 'select address_place_id';
			$sSQL .= ' FROM place_addressline';
			$sSQL .= " WHERE place_id = $iPlaceID";
			$sSQL .= " ORDER BY abs(cached_rank_address - $iMaxRank) asc,cached_rank_address desc,isaddress desc,distance desc";
			$sSQL .= ' LIMIT 1';
			$iPlaceID = chksql($this->oDB->getOne($sSQL), "Could not get parent for place.");
			if (!$iPlaceID) {
				$iPlaceID = $aPlace['place_id'];
			}
		}
		return array('place_id' => $iPlaceID,
					'type' => $bPlaceIsTiger ? 'tiger' : ($bPlaceIsLine ? 'interpolation' : 'osm'),
					'fraction' => ($bPlaceIsTiger || $bPlaceIsLine) ? $fFraction : -1);
	}
}

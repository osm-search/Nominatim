<?php
	class ReverseGeocode
	{
		protected $oDB;

		protected $fLat;
		protected $fLon;
		protected $iMaxRank = 28;

		protected $aLangPrefOrder = array();

		protected $bShowAddressDetails = true;

		function ReverseGeocode(&$oDB)
		{
			$this->oDB =& $oDB;
		}

		function setLanguagePreference($aLangPref)
		{
			$this->aLangPrefOrder = $aLangPref;
		}

		function setIncludeAddressDetails($bAddressDetails = true)
		{
			$this->bAddressDetails = $bAddressDetails;
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

			// Find the nearest point
			$fSearchDiam = 0.0004;
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
				$sSQL .= ' and indexed_status = 0 ';
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
			}

			// The point we found might be too small - use the address to find what it is a child of
			if ($iPlaceID && $iMaxRank < 28)
			{
				if ($aPlace['rank_search'] > 28 && $iParentPlaceID)
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

			$oPlaceLookup = new PlaceLookup($this->oDB);
			$oPlaceLookup->setLanguagePreference($this->aLangPrefOrder);
			$oPlaceLookup->setIncludeAddressDetails($this->bAddressDetails);
			$oPlaceLookup->setPlaceId($iPlaceID);

			return $oPlaceLookup->lookup();
		}
	}
?>

<?php
	class Geocode
	{
		protected $oDB;

		protected $aLangPrefOrder = array();

		protected $bIncludeAddressDetails = false;

		protected $bIncludePolygonAsPoints = false;
		protected $bIncludePolygonAsText = false;
		protected $bIncludePolygonAsGeoJSON = false;
		protected $bIncludePolygonAsKML = false;
		protected $bIncludePolygonAsSVG = false;

		protected $aExcludePlaceIDs = array();
		protected $bDeDupe = true;
		protected $bReverseInPlan = false;

		protected $iLimit = 20;
		protected $iFinalLimit = 10;
		protected $iOffset = 0;

		protected $aCountryCodes = false;
		protected $aNearPoint = false;

		protected $bBoundedSearch = false;
		protected $aViewBox = false;
		protected $aRoutePoints = false;

		protected $iMaxRank = 20;
		protected $iMinAddressRank = 0;
		protected $iMaxAddressRank = 30;
		protected $aAddressRankList = array();

		protected $sAllowedTypesSQLList = false;

		protected $sQuery = false;
		protected $aStructuredQuery = false;

		function Geocode(&$oDB)
		{
			$this->oDB =& $oDB;
		}

		function setReverseInPlan($bReverse)
		{
			$this->bReverseInPlan = $bReverse;
		}

		function setLanguagePreference($aLangPref)
		{
			$this->aLangPrefOrder = $aLangPref;
		}

		function setIncludeAddressDetails($bAddressDetails = true)
		{
			$this->bIncludeAddressDetails = (bool)$bAddressDetails;
		}

		function getIncludeAddressDetails()
		{
			return $this->bIncludeAddressDetails;
		}

		function setIncludePolygonAsPoints($b = true)
		{
			$this->bIncludePolygonAsPoints = $b;
		}

		function getIncludePolygonAsPoints()
		{
			return $this->bIncludePolygonAsPoints;
		}

		function setIncludePolygonAsText($b = true)
		{
			$this->bIncludePolygonAsText = $b;
		}

		function getIncludePolygonAsText()
		{
			return $this->bIncludePolygonAsText;
		}

		function setIncludePolygonAsGeoJSON($b = true)
		{
			$this->bIncludePolygonAsGeoJSON = $b;
		}

		function setIncludePolygonAsKML($b = true)
		{
			$this->bIncludePolygonAsKML = $b;
		}

		function setIncludePolygonAsSVG($b = true)
		{
			$this->bIncludePolygonAsSVG = $b;
		}

		function setDeDupe($bDeDupe = true)
		{
			$this->bDeDupe = (bool)$bDeDupe;
		}

		function setLimit($iLimit = 10)
		{
			if ($iLimit > 50) $iLimit = 50;
			if ($iLimit < 1) $iLimit = 1;

			$this->iFinalLimit = $iLimit;
			$this->iLimit = $this->iFinalLimit + min($this->iFinalLimit, 10);
		}

		function setOffset($iOffset = 0)
		{
			$this->iOffset = $iOffset;
		}

		function setExcludedPlaceIDs($a)
		{
			// TODO: force to int
			$this->aExcludePlaceIDs = $a;
		}

		function getExcludedPlaceIDs()
		{
			return $this->aExcludePlaceIDs;
		}

		function setBounded($bBoundedSearch = true)
		{
			$this->bBoundedSearch = (bool)$bBoundedSearch;
		}

		function setViewBox($fLeft, $fBottom, $fRight, $fTop)
		{
			$this->aViewBox = array($fLeft, $fBottom, $fRight, $fTop);
		}

		function getViewBoxString()
		{
			if (!$this->aViewBox) return null;
			return $this->aViewBox[0].','.$this->aViewBox[3].','.$this->aViewBox[2].','.$this->aViewBox[1];
		}

		function setRoute($aRoutePoints)
		{
			$this->aRoutePoints = $aRoutePoints;
		}

		function setFeatureType($sFeatureType)
		{
			switch($sFeatureType)
			{
			case 'country':
				$this->setRankRange(4, 4);
				break;
			case 'state':
				$this->setRankRange(8, 8);
				break;
			case 'city':
				$this->setRankRange(14, 16);
				break;
			case 'settlement':
				$this->setRankRange(8, 20);
				break;
			}
		}

		function setRankRange($iMin, $iMax)
		{
			$this->iMinAddressRank = (int)$iMin;
			$this->iMaxAddressRank = (int)$iMax;
		}

		function setNearPoint($aNearPoint, $fRadiusDeg = 0.1)
		{
			$this->aNearPoint = array((float)$aNearPoint[0], (float)$aNearPoint[1], (float)$fRadiusDeg);
		}

		function setCountryCodesList($aCountryCodes)
		{
			$this->aCountryCodes = $aCountryCodes;
		}

		function setQuery($sQueryString)
		{
			$this->sQuery = $sQueryString;
			$this->aStructuredQuery = false;
		}

		function getQueryString()
		{
			return $this->sQuery;
		}

		function loadStructuredAddressElement($sValue, $sKey, $iNewMinAddressRank, $iNewMaxAddressRank, $aItemListValues)
		{
			$sValue = trim($sValue);
			if (!$sValue) return false;
			$this->aStructuredQuery[$sKey] = $sValue;
			if ($this->iMinAddressRank == 0 && $this->iMaxAddressRank == 30)
			{
				$this->iMinAddressRank = $iNewMinAddressRank;
				$this->iMaxAddressRank = $iNewMaxAddressRank;
			}
			if ($aItemListValues) $this->aAddressRankList = array_merge($this->aAddressRankList, $aItemListValues);
			return true;
		}

		function setStructuredQuery($sAmentiy = false, $sStreet = false, $sCity = false, $sCounty = false, $sState = false, $sCountry = false, $sPostalCode = false)
		{
			$this->sQuery = false;

			$this->aStructuredQuery = array();
			$this->sAllowedTypesSQLList = '';

			$this->loadStructuredAddressElement($sAmentiy, 'amenity', 26, 30, false);
			$this->loadStructuredAddressElement($sStreet, 'street', 26, 30, false);
			$this->loadStructuredAddressElement($sCity, 'city', 14, 24, false);
			$this->loadStructuredAddressElement($sCounty, 'county', 9, 13, false);
			$this->loadStructuredAddressElement($sState, 'state', 8, 8, false);
			$this->loadStructuredAddressElement($sPostalCode, 'postalcode' , 5, 11, array(5, 11));
			$this->loadStructuredAddressElement($sCountry, 'country', 4, 4, false);

			if (sizeof($this->aStructuredQuery) > 0) 
			{
				$this->sQuery = join(', ', $this->aStructuredQuery);
				if ($this->iMaxAddressRank < 30)
				{
					$sAllowedTypesSQLList = '(\'place\',\'boundary\')';
				}
			}

		}

		function getDetails($aPlaceIDs)
		{
			if (sizeof($aPlaceIDs) == 0)  return array();

			$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted",$this->aLangPrefOrder))."]";

			// Get the details for display (is this a redundant extra step?)
			$sPlaceIDs = join(',',$aPlaceIDs);

			$sSQL = "select osm_type,osm_id,class,type,admin_level,rank_search,rank_address,min(place_id) as place_id,calculated_country_code as country_code,";
			$sSQL .= "get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
			$sSQL .= "get_name_by_language(name, $sLanguagePrefArraySQL) as placename,";
			$sSQL .= "get_name_by_language(name, ARRAY['ref']) as ref,";
			$sSQL .= "avg(ST_X(centroid)) as lon,avg(ST_Y(centroid)) as lat, ";
			$sSQL .= "coalesce(importance,0.75-(rank_search::float/40)) as importance, ";
			$sSQL .= "(select max(p.importance*(p.rank_address+2)) from place_addressline s, placex p where s.place_id = min(placex.place_id) and p.place_id = s.address_place_id and s.isaddress and p.importance is not null) as addressimportance, ";
			$sSQL .= "(extratags->'place') as extra_place ";
			$sSQL .= "from placex where place_id in ($sPlaceIDs) ";
			$sSQL .= "and (placex.rank_address between $this->iMinAddressRank and $this->iMaxAddressRank ";
			if (14 >= $this->iMinAddressRank && 14 <= $this->iMaxAddressRank) $sSQL .= " OR (extratags->'place') = 'city'";
			if ($this->aAddressRankList) $sSQL .= " OR placex.rank_address in (".join(',',$this->aAddressRankList).")";
			$sSQL .= ") ";
			if ($this->sAllowedTypesSQLList) $sSQL .= "and placex.class in $this->sAllowedTypesSQLList ";
			$sSQL .= "and linked_place_id is null ";
			$sSQL .= "group by osm_type,osm_id,class,type,admin_level,rank_search,rank_address,calculated_country_code,importance";
			if (!$this->bDeDupe) $sSQL .= ",place_id";
			$sSQL .= ",langaddress ";
			$sSQL .= ",placename ";
			$sSQL .= ",ref ";
			$sSQL .= ",extratags->'place' ";

			if (30 >= $this->iMinAddressRank && 30 <= $this->iMaxAddressRank)
			{
				$sSQL .= " union ";
				$sSQL .= "select 'T' as osm_type,place_id as osm_id,'place' as class,'house' as type,null as admin_level,30 as rank_search,30 as rank_address,min(place_id) as place_id,'us' as country_code,";
				$sSQL .= "get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
				$sSQL .= "null as placename,";
				$sSQL .= "null as ref,";
				$sSQL .= "avg(ST_X(centroid)) as lon,avg(ST_Y(centroid)) as lat, ";
				$sSQL .= "-0.15 as importance, ";
				$sSQL .= "(select max(p.importance*(p.rank_address+2)) from place_addressline s, placex p where s.place_id = min(location_property_tiger.place_id) and p.place_id = s.address_place_id and s.isaddress and p.importance is not null) as addressimportance, ";
				$sSQL .= "null as extra_place ";
				$sSQL .= "from location_property_tiger where place_id in ($sPlaceIDs) ";
				$sSQL .= "and 30 between $this->iMinAddressRank and $this->iMaxAddressRank ";
				$sSQL .= "group by place_id";
				if (!$this->bDeDupe) $sSQL .= ",place_id";
				$sSQL .= " union ";
				$sSQL .= "select 'L' as osm_type,place_id as osm_id,'place' as class,'house' as type,null as admin_level,30 as rank_search,30 as rank_address,min(place_id) as place_id,'us' as country_code,";
				$sSQL .= "get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
				$sSQL .= "null as placename,";
				$sSQL .= "null as ref,";
				$sSQL .= "avg(ST_X(centroid)) as lon,avg(ST_Y(centroid)) as lat, ";
				$sSQL .= "-0.10 as importance, ";
				$sSQL .= "(select max(p.importance*(p.rank_address+2)) from place_addressline s, placex p where s.place_id = min(location_property_aux.place_id) and p.place_id = s.address_place_id and s.isaddress and p.importance is not null) as addressimportance, ";
				$sSQL .= "null as extra_place ";
				$sSQL .= "from location_property_aux where place_id in ($sPlaceIDs) ";
				$sSQL .= "and 30 between $this->iMinAddressRank and $this->iMaxAddressRank ";
				$sSQL .= "group by place_id";
				if (!$this->bDeDupe) $sSQL .= ",place_id";
				$sSQL .= ",get_address_by_language(place_id, $sLanguagePrefArraySQL) ";
			}

			$sSQL .= "order by importance desc";
			if (CONST_Debug) { echo "<hr>"; var_dump($sSQL); }
			$aSearchResults = $this->oDB->getAll($sSQL);

			if (PEAR::IsError($aSearchResults))
			{
				failInternalError("Could not get details for place.", $sSQL, $aSearchResults);
			}

			return $aSearchResults;
		}

		function lookup()
		{
			if (!$this->sQuery && !$this->aStructuredQuery) return false;

			$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted",$this->aLangPrefOrder))."]";

			$sCountryCodesSQL = false;
			if ($this->aCountryCodes && sizeof($this->aCountryCodes))
			{
				$sCountryCodesSQL = join(',', array_map('addQuotes', $this->aCountryCodes));
			}

			// Hack to make it handle "new york, ny" (and variants) correctly
			$sQuery = str_ireplace(array('New York, ny','new york, new york', 'New York ny','new york new york'), 'new york city, ny', $this->sQuery);

			// Conflicts between US state abreviations and various words for 'the' in different languages
			if (isset($this->aLangPrefOrder['name:en']))
			{
				$sQuery = preg_replace('/,\s*il\s*(,|$)/',', illinois\1', $sQuery);
				$sQuery = preg_replace('/,\s*al\s*(,|$)/',', alabama\1', $sQuery);
				$sQuery = preg_replace('/,\s*la\s*(,|$)/',', louisiana\1', $sQuery);
			}

			// View Box SQL
			$sViewboxCentreSQL = $sViewboxSmallSQL = $sViewboxLargeSQL = false;
			$bBoundingBoxSearch = false;
			if ($this->aViewBox)
			{
				$fHeight = $this->aViewBox[0]-$this->aViewBox[2];
				$fWidth = $this->aViewBox[1]-$this->aViewBox[3];
				$aBigViewBox[0] = $this->aViewBox[0] + $fHeight;
				$aBigViewBox[2] = $this->aViewBox[2] - $fHeight;
				$aBigViewBox[1] = $this->aViewBox[1] + $fWidth;
				$aBigViewBox[3] = $this->aViewBox[3] - $fWidth;

				$sViewboxSmallSQL = "ST_SetSRID(ST_MakeBox2D(ST_Point(".(float)$this->aViewBox[0].",".(float)$this->aViewBox[1]."),ST_Point(".(float)$this->aViewBox[2].",".(float)$this->aViewBox[3].")),4326)";
				$sViewboxLargeSQL = "ST_SetSRID(ST_MakeBox2D(ST_Point(".(float)$aBigViewBox[0].",".(float)$aBigViewBox[1]."),ST_Point(".(float)$aBigViewBox[2].",".(float)$aBigViewBox[3].")),4326)";
				$bBoundingBoxSearch = $this->bBoundedSearch;
			}

			// Route SQL
			if ($this->aRoutePoints)
			{
				$sViewboxCentreSQL = "ST_SetSRID('LINESTRING(";
				$bFirst = false;
				foreach($this->aRouteaPoints as $aPoint)
				{
					if (!$bFirst) $sViewboxCentreSQL .= ",";
					$sViewboxCentreSQL .= $aPoint[1].' '.$aPoint[0];
				}
				$sViewboxCentreSQL .= ")'::geometry,4326)";

				$sSQL = "select st_buffer(".$sViewboxCentreSQL.",".(float)($_GET['routewidth']/69).")";
				$sViewboxSmallSQL = $this->oDB->getOne($sSQL);
				if (PEAR::isError($sViewboxSmallSQL))
				{
					failInternalError("Could not get small viewbox.", $sSQL, $sViewboxSmallSQL);
				}
				$sViewboxSmallSQL = "'".$sViewboxSmallSQL."'::geometry";

				$sSQL = "select st_buffer(".$sViewboxCentreSQL.",".(float)($_GET['routewidth']/30).")";
				$sViewboxLargeSQL = $this->oDB->getOne($sSQL);
				if (PEAR::isError($sViewboxLargeSQL))
				{
					failInternalError("Could not get large viewbox.", $sSQL, $sViewboxLargeSQL);
				}
				$sViewboxLargeSQL = "'".$sViewboxLargeSQL."'::geometry";
				$bBoundingBoxSearch = $this->bBoundedSearch;
			}

			// Do we have anything that looks like a lat/lon pair?
			if (preg_match('/\\b([NS])[ ]+([0-9]+[0-9.]*)[ ]+([0-9.]+)?[, ]+([EW])[ ]+([0-9]+)[ ]+([0-9]+[0-9.]*)?\\b/', $sQuery, $aData))
			{
				$fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60);
				$fQueryLon = ($aData[4]=='E'?1:-1) * ($aData[5] + $aData[6]/60);
				if ($fQueryLat <= 90.1 && $fQueryLat >= -90.1 && $fQueryLon <= 180.1 && $fQueryLon >= -180.1)
				{
					$this->setNearPoint(array($fQueryLat, $fQueryLon));
					$sQuery = trim(str_replace($aData[0], ' ', $sQuery));
				}
			}
			elseif (preg_match('/\\b([0-9]+)[ ]+([0-9]+[0-9.]*)?[ ]+([NS])[, ]+([0-9]+)[ ]+([0-9]+[0-9.]*)?[ ]+([EW])\\b/', $sQuery, $aData))
			{
				$fQueryLat = ($aData[3]=='N'?1:-1) * ($aData[1] + $aData[2]/60);
				$fQueryLon = ($aData[6]=='E'?1:-1) * ($aData[4] + $aData[5]/60);
				if ($fQueryLat <= 90.1 && $fQueryLat >= -90.1 && $fQueryLon <= 180.1 && $fQueryLon >= -180.1)
				{
					$this->setNearPoint(array($fQueryLat, $fQueryLon));
					$sQuery = trim(str_replace($aData[0], ' ', $sQuery));
				}
			}
			elseif (preg_match('/(\\[|^|\\b)(-?[0-9]+[0-9]*\\.[0-9]+)[, ]+(-?[0-9]+[0-9]*\\.[0-9]+)(\\]|$|\\b)/', $sQuery, $aData))
			{
				$fQueryLat = $aData[2];
				$fQueryLon = $aData[3];
				if ($fQueryLat <= 90.1 && $fQueryLat >= -90.1 && $fQueryLon <= 180.1 && $fQueryLon >= -180.1)
				{
					$this->setNearPoint(array($fQueryLat, $fQueryLon));
					$sQuery = trim(str_replace($aData[0], ' ', $sQuery));
				}
			}

			$aSearchResults = array();
			if ($sQuery || $this->aStructuredQuery)
			{
				// Start with a blank search
				$aSearches = array(
					array('iSearchRank' => 0, 'iNamePhrase' => -1, 'sCountryCode' => false, 'aName'=>array(), 'aAddress'=>array(), 'aFullNameAddress'=>array(),
					      'aNameNonSearch'=>array(), 'aAddressNonSearch'=>array(),
					      'sOperator'=>'', 'aFeatureName' => array(), 'sClass'=>'', 'sType'=>'', 'sHouseNumber'=>'', 'fLat'=>'', 'fLon'=>'', 'fRadius'=>'')
				);

				// Do we have a radius search?
				$sNearPointSQL = false;
				if ($this->aNearPoint)
				{
					$sNearPointSQL = "ST_SetSRID(ST_Point(".(float)$this->aNearPoint[1].",".(float)$this->aNearPoint[0]."),4326)";
					$aSearches[0]['fLat'] = (float)$this->aNearPoint[0];
					$aSearches[0]['fLon'] = (float)$this->aNearPoint[1];
					$aSearches[0]['fRadius'] = (float)$this->aNearPoint[2];
				}

				// Any 'special' terms in the search?
				$bSpecialTerms = false;
				preg_match_all('/\\[(.*)=(.*)\\]/', $sQuery, $aSpecialTermsRaw, PREG_SET_ORDER);
				$aSpecialTerms = array();
				foreach($aSpecialTermsRaw as $aSpecialTerm)
				{
					$sQuery = str_replace($aSpecialTerm[0], ' ', $sQuery);
					$aSpecialTerms[strtolower($aSpecialTerm[1])] = $aSpecialTerm[2];
				}

				preg_match_all('/\\[([\\w ]*)\\]/u', $sQuery, $aSpecialTermsRaw, PREG_SET_ORDER);
				$aSpecialTerms = array();
				if (isset($aStructuredQuery['amenity']) && $aStructuredQuery['amenity'])
				{
					$aSpecialTermsRaw[] = array('['.$aStructuredQuery['amenity'].']', $aStructuredQuery['amenity']);
					unset($aStructuredQuery['amenity']);
				}
				foreach($aSpecialTermsRaw as $aSpecialTerm)
				{
					$sQuery = str_replace($aSpecialTerm[0], ' ', $sQuery);
					$sToken = $this->oDB->getOne("select make_standard_name('".$aSpecialTerm[1]."') as string");
					$sSQL = 'select * from (select word_id,word_token, word, class, type, country_code, operator';
					$sSQL .= ' from word where word_token in (\' '.$sToken.'\')) as x where (class is not null and class not in (\'place\')) or country_code is not null';
					if (CONST_Debug) var_Dump($sSQL);
					$aSearchWords = $this->oDB->getAll($sSQL);
					$aNewSearches = array();
					foreach($aSearches as $aSearch)
					{
						foreach($aSearchWords as $aSearchTerm)
						{
							$aNewSearch = $aSearch;
							if ($aSearchTerm['country_code'])
							{
								$aNewSearch['sCountryCode'] = strtolower($aSearchTerm['country_code']);
								$aNewSearches[] = $aNewSearch;
								$bSpecialTerms = true;
							}
							if ($aSearchTerm['class'])
							{
								$aNewSearch['sClass'] = $aSearchTerm['class'];
								$aNewSearch['sType'] = $aSearchTerm['type'];
								$aNewSearches[] = $aNewSearch;
								$bSpecialTerms = true;
							}
						}
					}
					$aSearches = $aNewSearches;
				}

				// Split query into phrases
				// Commas are used to reduce the search space by indicating where phrases split
				if ($this->aStructuredQuery)
				{
					$aPhrases = $this->aStructuredQuery;
					$bStructuredPhrases = true;
				}
				else
				{
					$aPhrases = explode(',',$sQuery);
					$bStructuredPhrases = false;
				}

				// Convert each phrase to standard form
				// Create a list of standard words
				// Get all 'sets' of words
				// Generate a complete list of all
				$aTokens = array();
				foreach($aPhrases as $iPhrase => $sPhrase)
				{
					$aPhrase = $this->oDB->getRow("select make_standard_name('".pg_escape_string($sPhrase)."') as string");
					if (PEAR::isError($aPhrase))
					{
						userError("Illegal query string (not an UTF-8 string): ".$sPhrase);
						if (CONST_Debug) var_dump($aPhrase);
						exit;
					}
					if (trim($aPhrase['string']))
					{
						$aPhrases[$iPhrase] = $aPhrase;
						$aPhrases[$iPhrase]['words'] = explode(' ',$aPhrases[$iPhrase]['string']);
						$aPhrases[$iPhrase]['wordsets'] = getWordSets($aPhrases[$iPhrase]['words'], 0);
						$aTokens = array_merge($aTokens, getTokensFromSets($aPhrases[$iPhrase]['wordsets']));
					}
					else
					{
						unset($aPhrases[$iPhrase]);
					}
				}

				// Reindex phrases - we make assumptions later on that they are numerically keyed in order
				$aPhraseTypes = array_keys($aPhrases);
				$aPhrases = array_values($aPhrases);

				if (sizeof($aTokens))
				{
					// Check which tokens we have, get the ID numbers
					$sSQL = 'select word_id,word_token, word, class, type, country_code, operator, search_name_count';
					$sSQL .= ' from word where word_token in ('.join(',',array_map("getDBQuoted",$aTokens)).')';

					if (CONST_Debug) var_Dump($sSQL);

					$aValidTokens = array();
					if (sizeof($aTokens)) $aDatabaseWords = $this->oDB->getAll($sSQL);
					else $aDatabaseWords = array();
					if (PEAR::IsError($aDatabaseWords))
					{
						failInternalError("Could not get word tokens.", $sSQL, $aDatabaseWords);
					}
					$aPossibleMainWordIDs = array();
					$aWordFrequencyScores = array();
					foreach($aDatabaseWords as $aToken)
					{
						// Very special case - require 2 letter country param to match the country code found
						if ($bStructuredPhrases && $aToken['country_code'] && !empty($aStructuredQuery['country'])
								&& strlen($aStructuredQuery['country']) == 2 && strtolower($aStructuredQuery['country']) != $aToken['country_code'])
						{
							continue;
						}

						if (isset($aValidTokens[$aToken['word_token']]))
						{
							$aValidTokens[$aToken['word_token']][] = $aToken;
						}
						else
						{
							$aValidTokens[$aToken['word_token']] = array($aToken);
						}
						if (!$aToken['class'] && !$aToken['country_code']) $aPossibleMainWordIDs[$aToken['word_id']] = 1;
						$aWordFrequencyScores[$aToken['word_id']] = $aToken['search_name_count'] + 1;
					}
					if (CONST_Debug) var_Dump($aPhrases, $aValidTokens);

					// Try and calculate GB postcodes we might be missing
					foreach($aTokens as $sToken)
					{
						// Source of gb postcodes is now definitive - always use
						if (preg_match('/^([A-Z][A-Z]?[0-9][0-9A-Z]? ?[0-9])([A-Z][A-Z])$/', strtoupper(trim($sToken)), $aData))
						{
							if (substr($aData[1],-2,1) != ' ')
							{
								$aData[0] = substr($aData[0],0,strlen($aData[1]-1)).' '.substr($aData[0],strlen($aData[1]-1));
								$aData[1] = substr($aData[1],0,-1).' '.substr($aData[1],-1,1);
							}
							$aGBPostcodeLocation = gbPostcodeCalculate($aData[0], $aData[1], $aData[2], $this->oDB);
							if ($aGBPostcodeLocation)
							{
								$aValidTokens[$sToken] = $aGBPostcodeLocation;
							}
						}
						// US ZIP+4 codes - if there is no token,
						// 	merge in the 5-digit ZIP code
						else if (!isset($aValidTokens[$sToken]) && preg_match('/^([0-9]{5}) [0-9]{4}$/', $sToken, $aData))
						{
							if (isset($aValidTokens[$aData[1]]))
							{
								foreach($aValidTokens[$aData[1]] as $aToken)
								{
									if (!$aToken['class'])
									{
										if (isset($aValidTokens[$sToken]))
										{
											$aValidTokens[$sToken][] = $aToken;
										}
										else
										{
											$aValidTokens[$sToken] = array($aToken);
										}
									}
								}
							}
						}
					}

					foreach($aTokens as $sToken)
					{
						// Unknown single word token with a number - assume it is a house number
						if (!isset($aValidTokens[' '.$sToken]) && strpos($sToken,' ') === false && preg_match('/[0-9]/', $sToken))
						{
							$aValidTokens[' '.$sToken] = array(array('class'=>'place','type'=>'house'));
						}
					}

					// Any words that have failed completely?
					// TODO: suggestions

					// Start the search process
					$aResultPlaceIDs = array();

					/*
					   Calculate all searches using aValidTokens i.e.
					   'Wodsworth Road, Sheffield' =>

					   Phrase Wordset
					   0      0       (wodsworth road)
					   0      1       (wodsworth)(road)
					   1      0       (sheffield)

					   Score how good the search is so they can be ordered
					 */
					foreach($aPhrases as $iPhrase => $sPhrase)
					{
						$aNewPhraseSearches = array();
						if ($bStructuredPhrases) $sPhraseType = $aPhraseTypes[$iPhrase];
						else $sPhraseType = '';

						foreach($aPhrases[$iPhrase]['wordsets'] as $iWordSet => $aWordset)
						{
							// Too many permutations - too expensive
							if ($iWordSet > 120) break;

							$aWordsetSearches = $aSearches;

							// Add all words from this wordset
							foreach($aWordset as $iToken => $sToken)
							{
								//echo "<br><b>$sToken</b>";
								$aNewWordsetSearches = array();

								foreach($aWordsetSearches as $aCurrentSearch)
								{
									//echo "<i>";
									//var_dump($aCurrentSearch);
									//echo "</i>";

									// If the token is valid
									if (isset($aValidTokens[' '.$sToken]))
									{
										foreach($aValidTokens[' '.$sToken] as $aSearchTerm)
										{
											$aSearch = $aCurrentSearch;
											$aSearch['iSearchRank']++;
											if (($sPhraseType == '' || $sPhraseType == 'country') && !empty($aSearchTerm['country_code']) && $aSearchTerm['country_code'] != '0')
											{
												if ($aSearch['sCountryCode'] === false)
												{
													$aSearch['sCountryCode'] = strtolower($aSearchTerm['country_code']);
													// Country is almost always at the end of the string - increase score for finding it anywhere else (optimisation)
													// If reverse order is enabled, it may appear at the beginning as well.
													if (($iToken+1 != sizeof($aWordset) || $iPhrase+1 != sizeof($aPhrases)) &&
															(!$this->bReverseInPlan || $iToken > 0 || $iPhrase > 0))
													{
														$aSearch['iSearchRank'] += 5;
													}
													if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
												}
											}
											elseif (isset($aSearchTerm['lat']) && $aSearchTerm['lat'] !== '' && $aSearchTerm['lat'] !== null)
											{
												if ($aSearch['fLat'] === '')
												{
													$aSearch['fLat'] = $aSearchTerm['lat'];
													$aSearch['fLon'] = $aSearchTerm['lon'];
													$aSearch['fRadius'] = $aSearchTerm['radius'];
													if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
												}
											}
											elseif ($sPhraseType == 'postalcode')
											{
												// We need to try the case where the postal code is the primary element (i.e. no way to tell if it is (postalcode, city) OR (city, postalcode) so try both
												if (isset($aSearchTerm['word_id']) && $aSearchTerm['word_id'])
												{
													// If we already have a name try putting the postcode first
													if (sizeof($aSearch['aName']))
													{
														$aNewSearch = $aSearch;
														$aNewSearch['aAddress'] = array_merge($aNewSearch['aAddress'], $aNewSearch['aName']);
														$aNewSearch['aName'] = array();
														$aNewSearch['aName'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
														if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aNewSearch;
													}

													if (sizeof($aSearch['aName']))
													{
														if ((!$bStructuredPhrases || $iPhrase > 0) && $sPhraseType != 'country' && (!isset($aValidTokens[$sToken]) || strlen($sToken) < 4 || strpos($sToken, ' ') !== false))
														{
															$aSearch['aAddress'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
														}
														else
														{
															$aCurrentSearch['aFullNameAddress'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
															$aSearch['iSearchRank'] += 1000; // skip;
														}
													}
													else
													{
														$aSearch['aName'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
														//$aSearch['iNamePhrase'] = $iPhrase;
													}
													if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
												}

											}
											elseif (($sPhraseType == '' || $sPhraseType == 'street') && $aSearchTerm['class'] == 'place' && $aSearchTerm['type'] == 'house')
											{
												if ($aSearch['sHouseNumber'] === '')
												{
													$aSearch['sHouseNumber'] = $sToken;
													if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
													/*
													// Fall back to not searching for this item (better than nothing)
													$aSearch = $aCurrentSearch;
													$aSearch['iSearchRank'] += 1;
													if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
													 */
												}
											}
											elseif ($sPhraseType == '' && $aSearchTerm['class'] !== '' && $aSearchTerm['class'] !== null)
											{
												if ($aSearch['sClass'] === '')
												{
													$aSearch['sOperator'] = $aSearchTerm['operator'];
													$aSearch['sClass'] = $aSearchTerm['class'];
													$aSearch['sType'] = $aSearchTerm['type'];
													if (sizeof($aSearch['aName'])) $aSearch['sOperator'] = 'name';
													else $aSearch['sOperator'] = 'near'; // near = in for the moment

													// Do we have a shortcut id?
													if ($aSearch['sOperator'] == 'name')
													{
														$sSQL = "select get_tagpair('".$aSearch['sClass']."', '".$aSearch['sType']."')";
														if ($iAmenityID = $this->oDB->getOne($sSQL))
														{
															$aValidTokens[$aSearch['sClass'].':'.$aSearch['sType']] = array('word_id' => $iAmenityID);
															$aSearch['aName'][$iAmenityID] = $iAmenityID;
															$aSearch['sClass'] = '';
															$aSearch['sType'] = '';
														}
													}
													if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
												}
											}
											elseif (isset($aSearchTerm['word_id']) && $aSearchTerm['word_id'])
											{
												if (sizeof($aSearch['aName']))
												{
													if ((!$bStructuredPhrases || $iPhrase > 0) && $sPhraseType != 'country' && (!isset($aValidTokens[$sToken]) || strlen($sToken) < 4 || strpos($sToken, ' ') !== false))
													{
														$aSearch['aAddress'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
													}
													else
													{
														$aCurrentSearch['aFullNameAddress'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
														$aSearch['iSearchRank'] += 1000; // skip;
													}
												}
												else
												{
													$aSearch['aName'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
													//$aSearch['iNamePhrase'] = $iPhrase;
												}
												if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
											}
										}
									}
									if (isset($aValidTokens[$sToken]))
									{
										// Allow searching for a word - but at extra cost
										foreach($aValidTokens[$sToken] as $aSearchTerm)
										{
											if (isset($aSearchTerm['word_id']) && $aSearchTerm['word_id'])
											{
												if ((!$bStructuredPhrases || $iPhrase > 0) && sizeof($aCurrentSearch['aName']) && strlen($sToken) >= 4)
												{
													$aSearch = $aCurrentSearch;
													$aSearch['iSearchRank'] += 1;
													if ($aWordFrequencyScores[$aSearchTerm['word_id']] < CONST_Max_Word_Frequency)
													{
														$aSearch['aAddress'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
														if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
													}
													elseif (isset($aValidTokens[' '.$sToken])) // revert to the token version?
													{
														foreach($aValidTokens[' '.$sToken] as $aSearchTermToken)
														{
															if (empty($aSearchTermToken['country_code'])
																	&& empty($aSearchTermToken['lat'])
																	&& empty($aSearchTermToken['class']))
															{
																$aSearch = $aCurrentSearch;
																$aSearch['iSearchRank'] += 1;
																$aSearch['aAddress'][$aSearchTermToken['word_id']] = $aSearchTermToken['word_id'];
																if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
															}
														}
													}
													else
													{
														$aSearch['aAddressNonSearch'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
														if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
													}
												}

												if (!sizeof($aCurrentSearch['aName']) || $aCurrentSearch['iNamePhrase'] == $iPhrase)
												{
													$aSearch = $aCurrentSearch;
													$aSearch['iSearchRank'] += 2;
													if (preg_match('#^[0-9]+$#', $sToken)) $aSearch['iSearchRank'] += 2;
													if ($aWordFrequencyScores[$aSearchTerm['word_id']] < CONST_Max_Word_Frequency)
														$aSearch['aName'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
													else
														$aSearch['aNameNonSearch'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
													$aSearch['iNamePhrase'] = $iPhrase;
													if ($aSearch['iSearchRank'] < $this->iMaxRank) $aNewWordsetSearches[] = $aSearch;
												}
											}
										}
									}
									else
									{
										// Allow skipping a word - but at EXTREAM cost
										//$aSearch = $aCurrentSearch;
										//$aSearch['iSearchRank']+=100;
										//$aNewWordsetSearches[] = $aSearch;
									}
								}
								// Sort and cut
								usort($aNewWordsetSearches, 'bySearchRank');
								$aWordsetSearches = array_slice($aNewWordsetSearches, 0, 50);
							}
							//var_Dump('<hr>',sizeof($aWordsetSearches)); exit;

							$aNewPhraseSearches = array_merge($aNewPhraseSearches, $aNewWordsetSearches);
							usort($aNewPhraseSearches, 'bySearchRank');

							$aSearchHash = array();
							foreach($aNewPhraseSearches as $iSearch => $aSearch)
							{
								$sHash = serialize($aSearch);
								if (isset($aSearchHash[$sHash])) unset($aNewPhraseSearches[$iSearch]);
								else $aSearchHash[$sHash] = 1;
							}

							$aNewPhraseSearches = array_slice($aNewPhraseSearches, 0, 50);
						}

						// Re-group the searches by their score, junk anything over 20 as just not worth trying
						$aGroupedSearches = array();
						foreach($aNewPhraseSearches as $aSearch)
						{
							if ($aSearch['iSearchRank'] < $this->iMaxRank)
							{
								if (!isset($aGroupedSearches[$aSearch['iSearchRank']])) $aGroupedSearches[$aSearch['iSearchRank']] = array();
								$aGroupedSearches[$aSearch['iSearchRank']][] = $aSearch;
							}
						}
						ksort($aGroupedSearches);

						$iSearchCount = 0;
						$aSearches = array();
						foreach($aGroupedSearches as $iScore => $aNewSearches)
						{
							$iSearchCount += sizeof($aNewSearches);
							$aSearches = array_merge($aSearches, $aNewSearches);
							if ($iSearchCount > 50) break;
						}

						//if (CONST_Debug) _debugDumpGroupedSearches($aGroupedSearches, $aValidTokens);

					}

				}
				else
				{
					// Re-group the searches by their score, junk anything over 20 as just not worth trying
					$aGroupedSearches = array();
					foreach($aSearches as $aSearch)
					{
						if ($aSearch['iSearchRank'] < $this->iMaxRank)
						{
							if (!isset($aGroupedSearches[$aSearch['iSearchRank']])) $aGroupedSearches[$aSearch['iSearchRank']] = array();
							$aGroupedSearches[$aSearch['iSearchRank']][] = $aSearch;
						}
					}
					ksort($aGroupedSearches);
				}

				if (CONST_Debug) var_Dump($aGroupedSearches);

				if ($this->bReverseInPlan)
				{
					$aCopyGroupedSearches = $aGroupedSearches;
					foreach($aCopyGroupedSearches as $iGroup => $aSearches)
					{
						foreach($aSearches as $iSearch => $aSearch)
						{
							if (sizeof($aSearch['aAddress']))
							{
								$iReverseItem = array_pop($aSearch['aAddress']);
								if (isset($aPossibleMainWordIDs[$iReverseItem]))
								{
									$aSearch['aAddress'] = array_merge($aSearch['aAddress'], $aSearch['aName']);
									$aSearch['aName'] = array($iReverseItem);
									$aGroupedSearches[$iGroup][] = $aSearch;
								}
								//$aReverseSearch['aName'][$iReverseItem] = $iReverseItem;
								//$aGroupedSearches[$iGroup][] = $aReverseSearch;
							}
						}
					}
				}

				if (CONST_Search_TryDroppedAddressTerms && sizeof($aStructuredQuery) > 0)
				{
					$aCopyGroupedSearches = $aGroupedSearches;
					foreach($aCopyGroupedSearches as $iGroup => $aSearches)
					{
						foreach($aSearches as $iSearch => $aSearch)
						{
							$aReductionsList = array($aSearch['aAddress']);
							$iSearchRank = $aSearch['iSearchRank'];
							while(sizeof($aReductionsList) > 0)
							{
								$iSearchRank += 5;
								if ($iSearchRank > iMaxRank) break 3;
								$aNewReductionsList = array();
								foreach($aReductionsList as $aReductionsWordList)
								{
									for ($iReductionWord = 0; $iReductionWord < sizeof($aReductionsWordList); $iReductionWord++)
									{
										$aReductionsWordListResult = array_merge(array_slice($aReductionsWordList, 0, $iReductionWord), array_slice($aReductionsWordList, $iReductionWord+1));
										$aReverseSearch = $aSearch;
										$aSearch['aAddress'] = $aReductionsWordListResult;
										$aSearch['iSearchRank'] = $iSearchRank;
										$aGroupedSearches[$iSearchRank][] = $aReverseSearch;
										if (sizeof($aReductionsWordListResult) > 0)
										{
											$aNewReductionsList[] = $aReductionsWordListResult;
										}
									}
								}
								$aReductionsList = $aNewReductionsList;
							}
						}
					}
					ksort($aGroupedSearches);
				}

				// Filter out duplicate searches
				$aSearchHash = array();
				foreach($aGroupedSearches as $iGroup => $aSearches)
				{
					foreach($aSearches as $iSearch => $aSearch)
					{
						$sHash = serialize($aSearch);
						if (isset($aSearchHash[$sHash]))
						{
							unset($aGroupedSearches[$iGroup][$iSearch]);
							if (sizeof($aGroupedSearches[$iGroup]) == 0) unset($aGroupedSearches[$iGroup]);
						}
						else
						{
							$aSearchHash[$sHash] = 1;
						}
					}
				}

				if (CONST_Debug) _debugDumpGroupedSearches($aGroupedSearches, $aValidTokens);

				$iGroupLoop = 0;
				$iQueryLoop = 0;
				foreach($aGroupedSearches as $iGroupedRank => $aSearches)
				{
					$iGroupLoop++;
					foreach($aSearches as $aSearch)
					{
						$iQueryLoop++;

						if (CONST_Debug) { echo "<hr><b>Search Loop, group $iGroupLoop, loop $iQueryLoop</b>"; }
						if (CONST_Debug) _debugDumpGroupedSearches(array($iGroupedRank => array($aSearch)), $aValidTokens);

						// No location term?
						if (!sizeof($aSearch['aName']) && !sizeof($aSearch['aAddress']) && !$aSearch['fLon'])
						{
							if ($aSearch['sCountryCode'] && !$aSearch['sClass'] && !$aSearch['sHouseNumber'])
							{
								// Just looking for a country by code - look it up
								if (4 >= $this->iMinAddressRank && 4 <= $this->iMaxAddressRank)
								{
									$sSQL = "select place_id from placex where calculated_country_code='".$aSearch['sCountryCode']."' and rank_search = 4";
									if ($sCountryCodesSQL) $sSQL .= " and calculated_country_code in ($sCountryCodesSQL)";
									$sSQL .= " order by st_area(geometry) desc limit 1";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $this->oDB->getCol($sSQL);
								}
							}
							else
							{
								if (!$bBoundingBoxSearch && !$aSearch['fLon']) continue;
								if (!$aSearch['sClass']) continue;
								$sSQL = "select count(*) from pg_tables where tablename = 'place_classtype_".$aSearch['sClass']."_".$aSearch['sType']."'";
								if ($this->oDB->getOne($sSQL))
								{
									$sSQL = "select place_id from place_classtype_".$aSearch['sClass']."_".$aSearch['sType']." ct";
									if ($sCountryCodesSQL) $sSQL .= " join placex using (place_id)";
									$sSQL .= " where st_contains($sViewboxSmallSQL, ct.centroid)";
									if ($sCountryCodesSQL) $sSQL .= " and calculated_country_code in ($sCountryCodesSQL)";
									if (sizeof($this->aExcludePlaceIDs))
									{
										$sSQL .= " and place_id not in (".join(',',$this->aExcludePlaceIDs).")";
									}
									if ($sViewboxCentreSQL) $sSQL .= " order by st_distance($sViewboxCentreSQL, ct.centroid) asc";
									$sSQL .= " limit $this->iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $this->oDB->getCol($sSQL);

									// If excluded place IDs are given, it is fair to assume that
									// there have been results in the small box, so no further
									// expansion in that case.
									if (!sizeof($aPlaceIDs) && !sizeof($this->aExcludePlaceIDs))
									{
										$sSQL = "select place_id from place_classtype_".$aSearch['sClass']."_".$aSearch['sType']." ct";
										if ($sCountryCodesSQL) $sSQL .= " join placex using (place_id)";
										$sSQL .= " where st_contains($sViewboxLargeSQL, ct.centroid)";
										if ($sCountryCodesSQL) $sSQL .= " and calculated_country_code in ($sCountryCodesSQL)";
										if ($sViewboxCentreSQL) $sSQL .= " order by st_distance($sViewboxCentreSQL, ct.centroid) asc";
										$sSQL .= " limit $this->iLimit";
										if (CONST_Debug) var_dump($sSQL);
										$aPlaceIDs = $this->oDB->getCol($sSQL);
									}
								}
								else
								{
									$sSQL = "select place_id from placex where class='".$aSearch['sClass']."' and type='".$aSearch['sType']."'";
									$sSQL .= " and st_contains($sViewboxSmallSQL, geometry) and linked_place_id is null";
									if ($sCountryCodesSQL) $sSQL .= " and calculated_country_code in ($sCountryCodesSQL)";
									if ($sViewboxCentreSQL)	$sSQL .= " order by st_distance($sViewboxCentreSQL, centroid) asc";
									$sSQL .= " limit $this->iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $this->oDB->getCol($sSQL);
								}
							}
						}
						else
						{
							$aPlaceIDs = array();

							// First we need a position, either aName or fLat or both
							$aTerms = array();
							$aOrder = array();

							// TODO: filter out the pointless search terms (2 letter name tokens and less)
							// they might be right - but they are just too darned expensive to run
							if (sizeof($aSearch['aName'])) $aTerms[] = "name_vector @> ARRAY[".join($aSearch['aName'],",")."]";
							if (sizeof($aSearch['aNameNonSearch'])) $aTerms[] = "array_cat(name_vector,ARRAY[]::integer[]) @> ARRAY[".join($aSearch['aNameNonSearch'],",")."]";
							if (sizeof($aSearch['aAddress']) && $aSearch['aName'] != $aSearch['aAddress'])
							{
								// For infrequent name terms disable index usage for address
								if (CONST_Search_NameOnlySearchFrequencyThreshold &&
										sizeof($aSearch['aName']) == 1 &&
										$aWordFrequencyScores[$aSearch['aName'][reset($aSearch['aName'])]] < CONST_Search_NameOnlySearchFrequencyThreshold)
								{
									$aTerms[] = "array_cat(nameaddress_vector,ARRAY[]::integer[]) @> ARRAY[".join(array_merge($aSearch['aAddress'],$aSearch['aAddressNonSearch']),",")."]";
								}
								else
								{
									$aTerms[] = "nameaddress_vector @> ARRAY[".join($aSearch['aAddress'],",")."]";
									if (sizeof($aSearch['aAddressNonSearch'])) $aTerms[] = "array_cat(nameaddress_vector,ARRAY[]::integer[]) @> ARRAY[".join($aSearch['aAddressNonSearch'],",")."]";
								}
							}
							if ($aSearch['sCountryCode']) $aTerms[] = "country_code = '".pg_escape_string($aSearch['sCountryCode'])."'";
							if ($aSearch['sHouseNumber']) $aTerms[] = "address_rank between 16 and 27";
							if ($aSearch['fLon'] && $aSearch['fLat'])
							{
								$aTerms[] = "ST_DWithin(centroid, ST_SetSRID(ST_Point(".$aSearch['fLon'].",".$aSearch['fLat']."),4326), ".$aSearch['fRadius'].")";
								$aOrder[] = "ST_Distance(centroid, ST_SetSRID(ST_Point(".$aSearch['fLon'].",".$aSearch['fLat']."),4326)) ASC";
							}
							if (sizeof($this->aExcludePlaceIDs))
							{
								$aTerms[] = "place_id not in (".join(',',$this->aExcludePlaceIDs).")";
							}
							if ($sCountryCodesSQL)
							{
								$aTerms[] = "country_code in ($sCountryCodesSQL)";
							}

							if ($bBoundingBoxSearch) $aTerms[] = "centroid && $sViewboxSmallSQL";
							if ($sNearPointSQL) $aOrder[] = "ST_Distance($sNearPointSQL, centroid) asc";

							$sImportanceSQL = '(case when importance = 0 OR importance IS NULL then 0.75-(search_rank::float/40) else importance end)';
							if ($sViewboxSmallSQL) $sImportanceSQL .= " * case when ST_Contains($sViewboxSmallSQL, centroid) THEN 1 ELSE 0.5 END";
							if ($sViewboxLargeSQL) $sImportanceSQL .= " * case when ST_Contains($sViewboxLargeSQL, centroid) THEN 1 ELSE 0.5 END";
							$aOrder[] = "$sImportanceSQL DESC";
							if (sizeof($aSearch['aFullNameAddress']))
							{
								$aOrder[] = '(select count(*) from (select unnest(ARRAY['.join($aSearch['aFullNameAddress'],",").']) INTERSECT select unnest(nameaddress_vector))s) DESC';
							}

							if (sizeof($aTerms))
							{
								$sSQL = "select place_id";
								$sSQL .= " from search_name";
								$sSQL .= " where ".join(' and ',$aTerms);
								$sSQL .= " order by ".join(', ',$aOrder);
								if ($aSearch['sHouseNumber'] || $aSearch['sClass'])
									$sSQL .= " limit 50";
								elseif (!sizeof($aSearch['aName']) && !sizeof($aSearch['aAddress']) && $aSearch['sClass'])
									$sSQL .= " limit 1";
								else
									$sSQL .= " limit ".$this->iLimit;

								if (CONST_Debug) { var_dump($sSQL); }
								$aViewBoxPlaceIDs = $this->oDB->getAll($sSQL);
								if (PEAR::IsError($aViewBoxPlaceIDs))
								{
									failInternalError("Could not get places for search terms.", $sSQL, $aViewBoxPlaceIDs);
								}
								//var_dump($aViewBoxPlaceIDs);
								// Did we have an viewbox matches?
								$aPlaceIDs = array();
								$bViewBoxMatch = false;
								foreach($aViewBoxPlaceIDs as $aViewBoxRow)
								{
									//if ($bViewBoxMatch == 1 && $aViewBoxRow['in_small'] == 'f') break;
									//if ($bViewBoxMatch == 2 && $aViewBoxRow['in_large'] == 'f') break;
									//if ($aViewBoxRow['in_small'] == 't') $bViewBoxMatch = 1;
									//else if ($aViewBoxRow['in_large'] == 't') $bViewBoxMatch = 2;
									$aPlaceIDs[] = $aViewBoxRow['place_id'];
								}
							}
							//var_Dump($aPlaceIDs);
							//exit;

							if ($aSearch['sHouseNumber'] && sizeof($aPlaceIDs))
							{
								$aRoadPlaceIDs = $aPlaceIDs;
								$sPlaceIDs = join(',',$aPlaceIDs);

								// Now they are indexed look for a house attached to a street we found
								$sHouseNumberRegex = '\\\\m'.str_replace(' ','[-,/ ]',$aSearch['sHouseNumber']).'\\\\M';
								$sSQL = "select place_id from placex where parent_place_id in (".$sPlaceIDs.") and housenumber ~* E'".$sHouseNumberRegex."'";
								if (sizeof($this->aExcludePlaceIDs))
								{
									$sSQL .= " and place_id not in (".join(',',$this->aExcludePlaceIDs).")";
								}
								$sSQL .= " limit $this->iLimit";
								if (CONST_Debug) var_dump($sSQL);
								$aPlaceIDs = $this->oDB->getCol($sSQL);

								// If not try the aux fallback table
								if (!sizeof($aPlaceIDs))
								{
									$sSQL = "select place_id from location_property_aux where parent_place_id in (".$sPlaceIDs.") and housenumber = '".pg_escape_string($aSearch['sHouseNumber'])."'";
									if (sizeof($this->aExcludePlaceIDs))
									{
										$sSQL .= " and place_id not in (".join(',',$this->aExcludePlaceIDs).")";
									}
									//$sSQL .= " limit $this->iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $this->oDB->getCol($sSQL);
								}

								if (!sizeof($aPlaceIDs))
								{
									$sSQL = "select place_id from location_property_tiger where parent_place_id in (".$sPlaceIDs.") and housenumber = '".pg_escape_string($aSearch['sHouseNumber'])."'";
									if (sizeof($this->aExcludePlaceIDs))
									{
										$sSQL .= " and place_id not in (".join(',',$this->aExcludePlaceIDs).")";
									}
									//$sSQL .= " limit $this->iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $this->oDB->getCol($sSQL);
								}

								// Fallback to the road
								if (!sizeof($aPlaceIDs) && preg_match('/[0-9]+/', $aSearch['sHouseNumber']))
								{
									$aPlaceIDs = $aRoadPlaceIDs;
								}

							}

							if ($aSearch['sClass'] && sizeof($aPlaceIDs))
							{
								$sPlaceIDs = join(',',$aPlaceIDs);
								$aClassPlaceIDs = array();

								if (!$aSearch['sOperator'] || $aSearch['sOperator'] == 'name')
								{
									// If they were searching for a named class (i.e. 'Kings Head pub') then we might have an extra match
									$sSQL = "select place_id from placex where place_id in ($sPlaceIDs) and class='".$aSearch['sClass']."' and type='".$aSearch['sType']."'";
									$sSQL .= " and linked_place_id is null";
									if ($sCountryCodesSQL) $sSQL .= " and calculated_country_code in ($sCountryCodesSQL)";
									$sSQL .= " order by rank_search asc limit $this->iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aClassPlaceIDs = $this->oDB->getCol($sSQL);
								}

								if (!$aSearch['sOperator'] || $aSearch['sOperator'] == 'near') // & in
								{
									$sSQL = "select count(*) from pg_tables where tablename = 'place_classtype_".$aSearch['sClass']."_".$aSearch['sType']."'";
									$bCacheTable = $this->oDB->getOne($sSQL);

									$sSQL = "select min(rank_search) from placex where place_id in ($sPlaceIDs)";

									if (CONST_Debug) var_dump($sSQL);
									$this->iMaxRank = ((int)$this->oDB->getOne($sSQL));

									// For state / country level searches the normal radius search doesn't work very well
									$sPlaceGeom = false;
									if ($this->iMaxRank < 9 && $bCacheTable)
									{
										// Try and get a polygon to search in instead
										$sSQL = "select geometry from placex where place_id in ($sPlaceIDs) and rank_search < $this->iMaxRank + 5 and st_geometrytype(geometry) in ('ST_Polygon','ST_MultiPolygon') order by rank_search asc limit 1";
										if (CONST_Debug) var_dump($sSQL);
										$sPlaceGeom = $this->oDB->getOne($sSQL);
									}

									if ($sPlaceGeom)
									{
										$sPlaceIDs = false;
									}
									else
									{
										$this->iMaxRank += 5;
										$sSQL = "select place_id from placex where place_id in ($sPlaceIDs) and rank_search < $this->iMaxRank";
										if (CONST_Debug) var_dump($sSQL);
										$aPlaceIDs = $this->oDB->getCol($sSQL);
										$sPlaceIDs = join(',',$aPlaceIDs);
									}

									if ($sPlaceIDs || $sPlaceGeom)
									{

										$fRange = 0.01;
										if ($bCacheTable)
										{
											// More efficient - can make the range bigger
											$fRange = 0.05;

											$sOrderBySQL = '';
											if ($sNearPointSQL) $sOrderBySQL = "ST_Distance($sNearPointSQL, l.centroid)";
											else if ($sPlaceIDs) $sOrderBySQL = "ST_Distance(l.centroid, f.geometry)";
											else if ($sPlaceGeom) $sOrderBysSQL = "ST_Distance(st_centroid('".$sPlaceGeom."'), l.centroid)";

											$sSQL = "select distinct l.place_id".($sOrderBySQL?','.$sOrderBySQL:'')." from place_classtype_".$aSearch['sClass']."_".$aSearch['sType']." as l";
											if ($sCountryCodesSQL) $sSQL .= " join placex as lp using (place_id)";
											if ($sPlaceIDs)
											{
												$sSQL .= ",placex as f where ";
												$sSQL .= "f.place_id in ($sPlaceIDs) and ST_DWithin(l.centroid, f.centroid, $fRange) ";
											}
											if ($sPlaceGeom)
											{
												$sSQL .= " where ";
												$sSQL .= "ST_Contains('".$sPlaceGeom."', l.centroid) ";
											}
											if (sizeof($this->aExcludePlaceIDs))
											{
												$sSQL .= " and l.place_id not in (".join(',',$this->aExcludePlaceIDs).")";
											}
											if ($sCountryCodesSQL) $sSQL .= " and lp.calculated_country_code in ($sCountryCodesSQL)";
											if ($sOrderBySQL) $sSQL .= "order by ".$sOrderBySQL." asc";
											if ($iOffset) $sSQL .= " offset $iOffset";
											$sSQL .= " limit $this->iLimit";
											if (CONST_Debug) var_dump($sSQL);
											$aClassPlaceIDs = array_merge($aClassPlaceIDs, $this->oDB->getCol($sSQL));
										}
										else
										{
											if (isset($aSearch['fRadius']) && $aSearch['fRadius']) $fRange = $aSearch['fRadius'];

											$sOrderBySQL = '';
											if ($sNearPointSQL) $sOrderBySQL = "ST_Distance($sNearPointSQL, l.geometry)";
											else $sOrderBySQL = "ST_Distance(l.geometry, f.geometry)";

											$sSQL = "select distinct l.place_id".($sOrderBysSQL?','.$sOrderBysSQL:'')." from placex as l,placex as f where ";
											$sSQL .= "f.place_id in ( $sPlaceIDs) and ST_DWithin(l.geometry, f.centroid, $fRange) ";
											$sSQL .= "and l.class='".$aSearch['sClass']."' and l.type='".$aSearch['sType']."' ";
											if (sizeof($this->aExcludePlaceIDs))
											{
												$sSQL .= " and l.place_id not in (".join(',',$this->aExcludePlaceIDs).")";
											}
											if ($sCountryCodesSQL) $sSQL .= " and l.calculated_country_code in ($sCountryCodesSQL)";
											if ($sOrderBy) $sSQL .= "order by ".$OrderBysSQL." asc";
											if ($iOffset) $sSQL .= " offset $iOffset";
											$sSQL .= " limit $this->iLimit";
											if (CONST_Debug) var_dump($sSQL);
											$aClassPlaceIDs = array_merge($aClassPlaceIDs, $this->oDB->getCol($sSQL));
										}
									}
								}

								$aPlaceIDs = $aClassPlaceIDs;

							}

						}

						if (PEAR::IsError($aPlaceIDs))
						{
							failInternalError("Could not get place IDs from tokens." ,$sSQL, $aPlaceIDs);
						}

						if (CONST_Debug) { echo "<br><b>Place IDs:</b> "; var_Dump($aPlaceIDs); }

						foreach($aPlaceIDs as $iPlaceID)
						{
							$aResultPlaceIDs[$iPlaceID] = $iPlaceID;
						}
						if ($iQueryLoop > 20) break;
					}

					if (isset($aResultPlaceIDs) && sizeof($aResultPlaceIDs) && ($this->iMinAddressRank != 0 || $this->iMaxAddressRank != 30))
					{
						// Need to verify passes rank limits before dropping out of the loop (yuk!)
						$sSQL = "select place_id from placex where place_id in (".join(',',$aResultPlaceIDs).") ";
						$sSQL .= "and (placex.rank_address between $this->iMinAddressRank and $this->iMaxAddressRank ";
						if (14 >= $this->iMinAddressRank && 14 <= $this->iMaxAddressRank) $sSQL .= " OR (extratags->'place') = 'city'";
						if ($this->aAddressRankList) $sSQL .= " OR placex.rank_address in (".join(',',$this->aAddressRankList).")";
						$sSQL .= ") UNION select place_id from location_property_tiger where place_id in (".join(',',$aResultPlaceIDs).") ";
						$sSQL .= "and (30 between $this->iMinAddressRank and $this->iMaxAddressRank ";
						if ($this->aAddressRankList) $sSQL .= " OR 30 in (".join(',',$this->aAddressRankList).")";
						$sSQL .= ")";
						if (CONST_Debug) var_dump($sSQL);
						$aResultPlaceIDs = $this->oDB->getCol($sSQL);
					}

					//exit;
					if (isset($aResultPlaceIDs) && sizeof($aResultPlaceIDs)) break;
					if ($iGroupLoop > 4) break;
					if ($iQueryLoop > 30) break;
				}

				// Did we find anything?
				if (isset($aResultPlaceIDs) && sizeof($aResultPlaceIDs))
				{
					$aSearchResults = $this->getDetails($aResultPlaceIDs);
				}

			}
			else
			{
				// Just interpret as a reverse geocode
				$iPlaceID = geocodeReverse((float)$this->aNearPoint[0], (float)$this->aNearPoint[1]);
				if ($iPlaceID)
					$aSearchResults = $this->getDetails(array($iPlaceID));
				else
					$aSearchResults = array();
			}

			// No results? Done
			if (!sizeof($aSearchResults))
			{
				return array();
			}

			$aClassType = getClassTypesWithImportance();
			$aRecheckWords = preg_split('/\b/u',$sQuery);
			foreach($aRecheckWords as $i => $sWord)
			{
				if (!$sWord) unset($aRecheckWords[$i]);
			}

			foreach($aSearchResults as $iResNum => $aResult)
			{
				if (CONST_Search_AreaPolygons)
				{
					// Get the bounding box and outline polygon
					$sSQL = "select place_id,0 as numfeatures,st_area(geometry) as area,";
					$sSQL .= "ST_Y(centroid) as centrelat,ST_X(centroid) as centrelon,";
					$sSQL .= "ST_Y(ST_PointN(ST_ExteriorRing(Box2D(geometry)),4)) as minlat,ST_Y(ST_PointN(ST_ExteriorRing(Box2D(geometry)),2)) as maxlat,";
					$sSQL .= "ST_X(ST_PointN(ST_ExteriorRing(Box2D(geometry)),1)) as minlon,ST_X(ST_PointN(ST_ExteriorRing(Box2D(geometry)),3)) as maxlon";
					if ($this->bIncludePolygonAsGeoJSON) $sSQL .= ",ST_AsGeoJSON(geometry) as asgeojson";
					if ($this->bIncludePolygonAsKML) $sSQL .= ",ST_AsKML(geometry) as askml";
					if ($this->bIncludePolygonAsSVG) $sSQL .= ",ST_AsSVG(geometry) as assvg";
					if ($this->bIncludePolygonAsText || $this->bIncludePolygonAsPoints) $sSQL .= ",ST_AsText(geometry) as astext";
					$sSQL .= " from placex where place_id = ".$aResult['place_id'].' and st_geometrytype(Box2D(geometry)) = \'ST_Polygon\'';
					$aPointPolygon = $this->oDB->getRow($sSQL);
					if (PEAR::IsError($aPointPolygon))
					{
						failInternalError("Could not get outline.", $sSQL, $aPointPolygon);
					}

					if ($aPointPolygon['place_id'])
					{
						if ($this->bIncludePolygonAsGeoJSON) $aResult['asgeojson'] = $aPointPolygon['asgeojson'];
						if ($this->bIncludePolygonAsKML) $aResult['askml'] = $aPointPolygon['askml'];
						if ($this->bIncludePolygonAsSVG) $aResult['assvg'] = $aPointPolygon['assvg'];
						if ($this->bIncludePolygonAsText) $aResult['astext'] = $aPointPolygon['astext'];

						if ($aPointPolygon['centrelon'] !== null && $aPointPolygon['centrelat'] !== null )
						{
							$aResult['lat'] = $aPointPolygon['centrelat'];
							$aResult['lon'] = $aPointPolygon['centrelon'];
						}

						if ($this->bIncludePolygonAsPoints)
						{
							// Translate geometary string to point array
							if (preg_match('#POLYGON\\(\\(([- 0-9.,]+)#',$aPointPolygon['astext'],$aMatch))
							{
								preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/',$aMatch[1],$aPolyPoints,PREG_SET_ORDER);
							}
							elseif (preg_match('#MULTIPOLYGON\\(\\(\\(([- 0-9.,]+)#',$aPointPolygon['astext'],$aMatch))
							{
								preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/',$aMatch[1],$aPolyPoints,PREG_SET_ORDER);
							}
							elseif (preg_match('#POINT\\((-?[0-9.]+) (-?[0-9.]+)\\)#',$aPointPolygon['astext'],$aMatch))
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
						}

						// Output data suitable for display (points and a bounding box)
						if ($this->bIncludePolygonAsPoints && isset($aPolyPoints))
						{
							$aResult['aPolyPoints'] = array();
							foreach($aPolyPoints as $aPoint)
							{
								$aResult['aPolyPoints'][] = array($aPoint[1], $aPoint[2]);
							}
						}
						$aResult['aBoundingBox'] = array($aPointPolygon['minlat'],$aPointPolygon['maxlat'],$aPointPolygon['minlon'],$aPointPolygon['maxlon']);
					}
				}

				if ($aResult['extra_place'] == 'city')
				{
					$aResult['class'] = 'place';
					$aResult['type'] = 'city';
					$aResult['rank_search'] = 16;
				}

				if (!isset($aResult['aBoundingBox']))
				{
					// Default
					$fDiameter = 0.0001;

					if (isset($aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['defdiameter'])
							&& $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['defdiameter'])
					{
						$fDiameter = $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['defzoom'];
					}
					elseif (isset($aClassType[$aResult['class'].':'.$aResult['type']]['defdiameter'])
							&& $aClassType[$aResult['class'].':'.$aResult['type']]['defdiameter'])
					{
						$fDiameter = $aClassType[$aResult['class'].':'.$aResult['type']]['defdiameter'];
					}
					$fRadius = $fDiameter / 2;

					$iSteps = max(8,min(100,$fRadius * 3.14 * 100000));
					$fStepSize = (2*pi())/$iSteps;
					$aPolyPoints = array();
					for($f = 0; $f < 2*pi(); $f += $fStepSize)
					{
						$aPolyPoints[] = array('',$aResult['lon']+($fRadius*sin($f)),$aResult['lat']+($fRadius*cos($f)));
					}
					$aPointPolygon['minlat'] = $aResult['lat'] - $fRadius;
					$aPointPolygon['maxlat'] = $aResult['lat'] + $fRadius;
					$aPointPolygon['minlon'] = $aResult['lon'] - $fRadius;
					$aPointPolygon['maxlon'] = $aResult['lon'] + $fRadius;

					// Output data suitable for display (points and a bounding box)
					if ($this->bIncludePolygonAsPoints)
					{
						$aResult['aPolyPoints'] = array();
						foreach($aPolyPoints as $aPoint)
						{
							$aResult['aPolyPoints'][] = array($aPoint[1], $aPoint[2]);
						}
					}
					$aResult['aBoundingBox'] = array($aPointPolygon['minlat'],$aPointPolygon['maxlat'],$aPointPolygon['minlon'],$aPointPolygon['maxlon']);
				}

				// Is there an icon set for this type of result?
				if (isset($aClassType[$aResult['class'].':'.$aResult['type']]['icon'])
						&& $aClassType[$aResult['class'].':'.$aResult['type']]['icon'])
				{
					$aResult['icon'] = CONST_Website_BaseURL.'images/mapicons/'.$aClassType[$aResult['class'].':'.$aResult['type']]['icon'].'.p.20.png';
				}

				if (isset($aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['label'])
						&& $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['label'])
				{
					$aResult['label'] = $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['label'];
				}
				elseif (isset($aClassType[$aResult['class'].':'.$aResult['type']]['label'])
						&& $aClassType[$aResult['class'].':'.$aResult['type']]['label'])
				{
					$aResult['label'] = $aClassType[$aResult['class'].':'.$aResult['type']]['label'];
				}

				if ($this->bIncludeAddressDetails)
				{
					$aResult['address'] = getAddressDetails($this->oDB, $sLanguagePrefArraySQL, $aResult['place_id'], $aResult['country_code']);
					if ($aResult['extra_place'] == 'city' && !isset($aResult['address']['city']))
					{
						$aResult['address'] = array_merge(array('city' => array_shift(array_values($aResult['address']))), $aResult['address']);
					}
				}

				// Adjust importance for the number of exact string matches in the result
				$aResult['importance'] = max(0.001,$aResult['importance']);
				$iCountWords = 0;
				$sAddress = $aResult['langaddress'];
				foreach($aRecheckWords as $i => $sWord)
				{
					if (stripos($sAddress, $sWord)!==false) $iCountWords++;
				}

				$aResult['importance'] = $aResult['importance'] + ($iCountWords*0.1); // 0.1 is a completely arbitrary number but something in the range 0.1 to 0.5 would seem right

				$aResult['name'] = $aResult['langaddress'];
				$aResult['foundorder'] = -$aResult['addressimportance'];
				$aSearchResults[$iResNum] = $aResult;
			}
			uasort($aSearchResults, 'byImportance');

			$aOSMIDDone = array();
			$aClassTypeNameDone = array();
			$aToFilter = $aSearchResults;
			$aSearchResults = array();

			$bFirst = true;
			foreach($aToFilter as $iResNum => $aResult)
			{
				if ($aResult['type'] == 'administrative') $aResult['type'] = 'administrative';
				$this->aExcludePlaceIDs[$aResult['place_id']] = $aResult['place_id'];
				if ($bFirst)
				{
					$fLat = $aResult['lat'];
					$fLon = $aResult['lon'];
					if (isset($aResult['zoom'])) $iZoom = $aResult['zoom'];
					$bFirst = false;
				}
				if (!$this->bDeDupe || (!isset($aOSMIDDone[$aResult['osm_type'].$aResult['osm_id']])
							&& !isset($aClassTypeNameDone[$aResult['osm_type'].$aResult['class'].$aResult['type'].$aResult['name'].$aResult['admin_level']])))
				{
					$aOSMIDDone[$aResult['osm_type'].$aResult['osm_id']] = true;
					$aClassTypeNameDone[$aResult['osm_type'].$aResult['class'].$aResult['type'].$aResult['name'].$aResult['admin_level']] = true;
					$aSearchResults[] = $aResult;
				}

				// Absolute limit on number of results
				if (sizeof($aSearchResults) >= $this->iFinalLimit) break;
			}

			return $aSearchResults;

		} // end lookup()


	} // end class


/*
		if (isset($_GET['route']) && $_GET['route'] && isset($_GET['routewidth']) && $_GET['routewidth'])
		{
			$aPoints = explode(',',$_GET['route']);
			if (sizeof($aPoints) % 2 != 0)
			{
				userError("Uneven number of points");
				exit;
			}
			$sViewboxCentreSQL = "ST_SetSRID('LINESTRING(";
			$fPrevCoord = false;
		}
*/

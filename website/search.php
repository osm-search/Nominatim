<?php
	require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
	require_once(CONST_BasePath.'/lib/log.php');

	ini_set('memory_limit', '200M');
	$oDB =& getDB();

	// Display defaults
	$fLat = CONST_Default_Lat;
	$fLon = CONST_Default_Lon;
	$iZoom = CONST_Default_Zoom;
	$bBoundingBoxSearch = isset($_GET['bounded'])?(bool)$_GET['bounded']:false;
	$sOutputFormat = 'html';
	$aSearchResults = array();
	$aExcludePlaceIDs = array();
	$sSuggestion = $sSuggestionURL = false;
	$bDeDupe = isset($_GET['dedupe'])?(bool)$_GET['dedupe']:true;
	$bReverseInPlan = false;
	$iLimit = isset($_GET['limit'])?(int)$_GET['limit']:10;
	$iOffset = isset($_GET['offset'])?(int)$_GET['offset']:0;
	$iMaxRank = 20;
	if ($iLimit > 100) $iLimit = 100;

	// Format for output
	if (isset($_GET['format']) && ($_GET['format'] == 'html' || $_GET['format'] == 'xml' || $_GET['format'] == 'json' ||  $_GET['format'] == 'jsonv2'))
	{
		$sOutputFormat = $_GET['format'];
	}

	// Show / use polygons
	$bShowPolygons = isset($_GET['polygon']) && $_GET['polygon'];

	// Show address breakdown
	$bShowAddressDetails = isset($_GET['addressdetails']) && $_GET['addressdetails'];

	// Prefered language	
	$aLangPrefOrder = getPrefferedLangauges();
	if (isset($aLangPrefOrder['name:de'])) $bReverseInPlan = true;
	$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted",$aLangPrefOrder))."]";

	if (isset($_GET['exclude_place_ids']) && $_GET['exclude_place_ids'])
	{
		foreach(explode(',',$_GET['exclude_place_ids']) as $iExcludedPlaceID)
		{
			$iExcludedPlaceID = (int)$iExcludedPlaceID;
			if ($iExcludedPlaceID) $aExcludePlaceIDs[$iExcludedPlaceID] = $iExcludedPlaceID;
		}
	}
		
	// Search query
	$sQuery = (isset($_GET['q'])?trim($_GET['q']):'');
	if (!$sQuery && $_SERVER['PATH_INFO'] && $_SERVER['PATH_INFO'][0] == '/')
	{
		$sQuery = substr($_SERVER['PATH_INFO'], 1);

		// reverse order of '/' seperated string
		$aPhrases = explode('/', $sQuery);		
		$aPhrases = array_reverse($aPhrases); 
		$sQuery = join(', ',$aPhrases);
	}

	if ($sQuery)
	{
		$hLog = logStart($oDB, 'search', $sQuery, $aLangPrefOrder);

		// If we have a view box create the SQL
		// Small is the actual view box, Large is double (on each axis) that 
		$sViewboxCentreSQL = $sViewboxSmallSQL = $sViewboxLargeSQL = false;
		if (isset($_GET['viewboxlbrt']) && $_GET['viewboxlbrt'])
		{
			$aCoOrdinatesLBRT = explode(',',$_GET['viewboxlbrt']);
			$_GET['viewbox'] = $aCoOrdinatesLBRT[0].','.$aCoOrdinatesLBRT[3].','.$aCoOrdinatesLBRT[2].','.$aCoOrdinatesLBRT[1];
		}
		if (isset($_GET['viewbox']) && $_GET['viewbox'])
		{
			$aCoOrdinates = explode(',',$_GET['viewbox']);
			$sViewboxSmallSQL = "ST_SetSRID(ST_MakeBox2D(ST_Point(".(float)$aCoOrdinates[0].",".(float)$aCoOrdinates[1]."),ST_Point(".(float)$aCoOrdinates[2].",".(float)$aCoOrdinates[3].")),4326)";
			$fHeight = $aCoOrdinates[0]-$aCoOrdinates[2];
			$fWidth = $aCoOrdinates[1]-$aCoOrdinates[3];
			$aCoOrdinates[0] += $fHeight;
			$aCoOrdinates[2] -= $fHeight;
			$aCoOrdinates[1] += $fWidth;
			$aCoOrdinates[3] -= $fWidth;
			$sViewboxLargeSQL = "ST_SetSRID(ST_MakeBox2D(ST_Point(".(float)$aCoOrdinates[0].",".(float)$aCoOrdinates[1]."),ST_Point(".(float)$aCoOrdinates[2].",".(float)$aCoOrdinates[3].")),4326)";
		}
		if (isset($_GET['route']) && $_GET['route'] && isset($_GET['routewidth']) && $_GET['routewidth'])
		{
			$aPoints = explode(',',$_GET['route']);
			if (sizeof($aPoints) % 2 != 0)
			{
				echo "Uneven number of points";
				exit;
			}
			$sViewboxCentreSQL = "ST_SetSRID('LINESTRING(";
			$fPrevCoord = false;
			foreach($aPoints as $i => $fPoint)
			{
				if ($i%2)
				{
					if ($i != 1) $sViewboxCentreSQL .= ",";
					$sViewboxCentreSQL .= ((float)$fPoint).' '.$fPrevCoord;
				}
				else
				{
					$fPrevCoord = (float)$fPoint;
				}
			}
			$sViewboxCentreSQL .= ")'::geometry,4326)";

			$sSQL = "select st_buffer(".$sViewboxCentreSQL.",".(float)($_GET['routewidth']/69).")";
			$sViewboxSmallSQL = $oDB->getOne($sSQL);
			if (PEAR::isError($sViewboxSmallSQL))
			{
				var_dump($sViewboxSmallSQL);
				exit;
			}
			$sViewboxSmallSQL = "'".$sViewboxSmallSQL."'::geometry";

			$sSQL = "select st_buffer(".$sViewboxCentreSQL.",".(float)($_GET['routewidth']/30).")";
			$sViewboxLargeSQL = $oDB->getOne($sSQL);
			if (PEAR::isError($sViewboxLargeSQL))
			{
				var_dump($sViewboxLargeSQL);
				exit;
			}
			$sViewboxLargeSQL = "'".$sViewboxLargeSQL."'::geometry";
		}

		// Do we have anything that looks like a lat/lon pair?
		if (preg_match('/\\b([NS])[ ]+([0-9]+[0-9.]*)[ ]+([0-9.]+)?[, ]+([EW])[ ]+([0-9]+)[ ]+([0-9]+[0-9.]*)?\\b/', $sQuery, $aData))
		{
			$_GET['nearlat'] = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60);
			$_GET['nearlon'] = ($aData[4]=='E'?1:-1) * ($aData[5] + $aData[6]/60);
			$sQuery = trim(str_replace($aData[0], ' ', $sQuery));
		}
		elseif (preg_match('/\\b([0-9]+)[ ]+([0-9]+[0-9.]*)?[ ]+([NS])[, ]+([0-9]+)[ ]+([0-9]+[0-9.]*)?[ ]+([EW])\\b/', $sQuery, $aData))
		{
			$_GET['nearlat'] = ($aData[3]=='N'?1:-1) * ($aData[1] + $aData[2]/60);
			$_GET['nearlon'] = ($aData[6]=='E'?1:-1) * ($aData[4] + $aData[5]/60);
			$sQuery = trim(str_replace($aData[0], ' ', $sQuery));
		}
		elseif (preg_match('/(\\[|\\b)(-?[0-9]+[0-9.]*)[, ]+(-?[0-9]+[0-9.]*)(\\]|\\b])/', $sQuery, $aData))
		{
			$_GET['nearlat'] = $aData[2];
			$_GET['nearlon'] = $aData[3];
			$sQuery = trim(str_replace($aData[0], ' ', $sQuery));
		}

		if ($sQuery)
		{

			// Start with a blank search
			$aSearches = array(
				array('iSearchRank' => 0, 'iNamePhrase' => 0, 'sCountryCode' => false, 'aName'=>array(), 'aAddress'=>array(), 
					'sOperator'=>'', 'aFeatureName' => array(), 'sClass'=>'', 'sType'=>'', 'sHouseNumber'=>'', 'fLat'=>'', 'fLon'=>'', 'fRadius'=>'')
			);

			$sNearPointSQL = false;
			if (isset($_GET['nearlat']) && isset($_GET['nearlon']))
			{
				$sNearPointSQL = "ST_SetSRID(ST_Point(".(float)$_GET['nearlon'].",".$_GET['nearlat']."),4326)";
				$aSearches[0]['fLat'] = (float)$_GET['nearlat'];
				$aSearches[0]['fLon'] = (float)$_GET['nearlon'];
				$aSearches[0]['fRadius'] = 0.1;
			}

			$bSpecialTerms = false;
			preg_match_all('/\\[(.*)=(.*)\\]/', $sQuery, $aSpecialTermsRaw, PREG_SET_ORDER);
			$aSpecialTerms = array();
			foreach($aSpecialTermsRaw as $aSpecialTerm)
			{
				$sQuery = str_replace($aSpecialTerm[0], ' ', $sQuery);
				$aSpecialTerms[strtolower($aSpecialTerm[1])] = $aSpecialTerm[2];
			}

			preg_match_all('/\\[([a-zA-Z]*)\\]/', $sQuery, $aSpecialTermsRaw, PREG_SET_ORDER);
			$aSpecialTerms = array();
			foreach($aSpecialTermsRaw as $aSpecialTerm)
			{
				$sQuery = str_replace($aSpecialTerm[0], ' ', $sQuery);
				$sToken = $oDB->getOne("select make_standard_name('".$aSpecialTerm[1]."') as string");
				$sSQL = 'select * from (select word_id,word_token, word, class, type, location, country_code, operator';
				$sSQL .= ' from word where word_token in (\' '.$sToken.'\')) as x where (class is not null and class != \'place\') or country_code is not null';
				$aSearchWords = $oDB->getAll($sSQL);
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
			$aPhrases = explode(',',$sQuery);

			// Convert each phrase to standard form
			// Create a list of standard words
			// Get all 'sets' of words
			// Generate a complete list of all 
			$aTokens = array();
			foreach($aPhrases as $iPhrase => $sPhrase)
			{
				$aPhrase = $oDB->getRow("select make_standard_name('".pg_escape_string($sPhrase)."') as string");
				if (PEAR::isError($aPhrase))
				{
					var_dump($aPhrase);
					exit;
				}
				if (trim($aPhrase['string']))
				{
					$aPhrases[$iPhrase] = $aPhrase;
					$aPhrases[$iPhrase]['words'] = explode(' ',$aPhrases[$iPhrase]['string']);
					$aPhrases[$iPhrase]['wordsets'] = getWordSets($aPhrases[$iPhrase]['words']);
					$aTokens = array_merge($aTokens, getTokensFromSets($aPhrases[$iPhrase]['wordsets']));
				}
				else
				{
					unset($aPhrases[$iPhrase]);
				}
			}			

			// reindex phrases - we make assumptions later on
			$aPhrases = array_values($aPhrases);

			if (sizeof($aTokens))
			{

			// Check which tokens we have, get the ID numbers			
			$sSQL = 'select word_id,word_token, word, class, type, location, country_code, operator';
			$sSQL .= ' from word where word_token in ('.join(',',array_map("getDBQuoted",$aTokens)).')';
//			$sSQL .= ' group by word_token, word, class, type, location,country_code';

			if (CONST_Debug) var_Dump($sSQL);

			$aValidTokens = array();
			if (sizeof($aTokens))
				$aDatabaseWords = $oDB->getAll($sSQL);
			else
				$aDatabaseWords = array();
			if (PEAR::IsError($aDatabaseWords))
			{
				var_dump($sSQL, $aDatabaseWords);
				exit;
			}
			foreach($aDatabaseWords as $aToken)
			{
				if (isset($aValidTokens[$aToken['word_token']]))
				{
					$aValidTokens[$aToken['word_token']][] = $aToken;
				}
				else
				{
					$aValidTokens[$aToken['word_token']] = array($aToken);
				}
			}
			if (CONST_Debug) var_Dump($aPhrases, $aValidTokens);

                        $aSuggestion = array();
                        $bSuggestion = false;
			if (CONST_Suggestions_Enabled)
			{
				foreach($aPhrases as $iPhrase => $aPhrase)
				{
                	                if (!isset($aValidTokens[' '.$aPhrase['wordsets'][0][0]]))
                        	        {
                                	        $sQuotedPhrase = getDBQuoted(' '.$aPhrase['wordsets'][0][0]);
						$aSuggestionWords = getWordSuggestions($oDB, $aPhrase['wordsets'][0][0]);
						$aRow = $aSuggestionWords[0];
						if ($aRow && $aRow['word'])
                	                        {
                        	                        $aSuggestion[] = $aRow['word'];
                                	                $bSuggestion = true;
                                        	}
	                                        else
        	                                {
                	                                $aSuggestion[] = $aPhrase['string'];
                        	                }
	                                }
        	                        else
                	                {
                        	                $aSuggestion[] = $aPhrase['string'];
                                	}
				}
			}
			if ($bSuggestion) $sSuggestion = join(', ',$aSuggestion);

			// Try and calculate GB postcodes we might be missing
			foreach($aTokens as $sToken)
			{
				if (!isset($aValidTokens[$sToken]) && !isset($aValidTokens[' '.$sToken]) && preg_match('/^([A-Z][A-Z]?[0-9][0-9A-Z]? ?[0-9])([A-Z][A-Z])$/', strtoupper(trim($sToken)), $aData))
				{
					if (substr($aData[1],-2,1) != ' ')
					{
						$aData[0] = substr($aData[0],0,strlen($aData[1]-1)).' '.substr($aData[0],strlen($aData[1]-1));
						$aData[1] = substr($aData[1],0,-1).' '.substr($aData[1],-1,1);
					}
					$aGBPostcodeLocation = gbPostcodeCalculate($aData[0], $aData[1], $aData[2], $oDB);
					if ($aGBPostcodeLocation)
					{
						$aValidTokens[$sToken] = $aGBPostcodeLocation;
					}
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

					foreach($aPhrases[$iPhrase]['wordsets'] as $iWordset => $aWordset)
					{
						$aWordsetSearches = $aSearches;

						// Add all words from this wordset
						foreach($aWordset as $sToken)
						{
							$aNewWordsetSearches = array();
							
							foreach($aWordsetSearches as $aCurrentSearch)
							{
								// If the token is valid
								if (isset($aValidTokens[' '.$sToken]))
								{
									foreach($aValidTokens[' '.$sToken] as $aSearchTerm)
									{
										$aSearch = $aCurrentSearch;
										$aSearch['iSearchRank']++;
										if ($aSearchTerm['country_code'] !== null && $aSearchTerm['country_code'] != '0')
										{
											if ($aSearch['sCountryCode'] === false)
											{
												$aSearch['sCountryCode'] = strtolower($aSearchTerm['country_code']);
												// Country is almost always at the end of the string - increase score for finding it anywhere else (opimisation)
												if ($iWordset+1 != sizeof($aPhrases[$iPhrase]['wordsets']) || $iPhrase+1 != sizeof($aPhrases)) $aSearch['iSearchRank'] += 5;
												if ($aSearch['iSearchRank'] < $iMaxRank) $aNewWordsetSearches[] = $aSearch;
											}
										}
										elseif ($aSearchTerm['lat'] !== '' && $aSearchTerm['lat'] !== null)
										{
											if ($aSearch['fLat'] === '')
											{
												$aSearch['fLat'] = $aSearchTerm['lat'];
												$aSearch['fLon'] = $aSearchTerm['lon'];
												$aSearch['fRadius'] = $aSearchTerm['radius'];
												if ($aSearch['iSearchRank'] < $iMaxRank) $aNewWordsetSearches[] = $aSearch;
											}
										}
										elseif ($aSearchTerm['class'] == 'place' && $aSearchTerm['type'] == 'house')
										{
											if ($aSearch['sHouseNumber'] === '')
											{
												$aSearch['sHouseNumber'] = $sToken;
												if ($aSearch['iSearchRank'] < $iMaxRank) $aNewWordsetSearches[] = $aSearch;
/*
												// Fall back to not searching for this item (better than nothing)
												$aSearch = $aCurrentSearch;
												$aSearch['iSearchRank'] += 1;
												if ($aSearch['iSearchRank'] < $iMaxRank) $aNewWordsetSearches[] = $aSearch;
*/
											}
										}
										elseif ($aSearchTerm['class'] !== '' && $aSearchTerm['class'] !== null)
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
													if ($iAmenityID = $oDB->getOne($sSQL))
													{
														$aValidTokens[$aSearch['sClass'].':'.$aSearch['sType']] = array('word_id' => $iAmenityID);
														$aSearch['aName'][$iAmenityID] = $iAmenityID;
														$aSearch['sClass'] = '';
														$aSearch['sType'] = '';
													}
												}
												if ($aSearch['iSearchRank'] < $iMaxRank) $aNewWordsetSearches[] = $aSearch;
											}
										}
										else
										{
											if (sizeof($aSearch['aName']))
											{
												$aSearch['aAddress'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
											}
											else
											{
												$aSearch['aName'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
												$aSearch['iNamePhrase'] = $iPhrase;
											}
											if ($aSearch['iSearchRank'] < $iMaxRank) $aNewWordsetSearches[] = $aSearch;
										}
									}
								}
								if (isset($aValidTokens[$sToken]))
								{
									// Allow searching for a word - but at extra cost
									foreach($aValidTokens[$sToken] as $aSearchTerm)
									{
										$aSearch = $aCurrentSearch;
										$aSearch['iSearchRank']+=5;
//										$aSearch['aAddress'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
										if (!sizeof($aSearch['aName']) || $aSearch['iNamePhrase'] == $iPhrase)
										{
											$aSearch['aName'][$aSearchTerm['word_id']] = $aSearchTerm['word_id'];
											$aSearch['iNamePhrase'] = $iPhrase;
										}
										if ($aSearch['iSearchRank'] < $iMaxRank) $aNewWordsetSearches[] = $aSearch;
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
//						var_Dump('<hr>',sizeof($aWordsetSearches)); exit;

						$aNewPhraseSearches = array_merge($aNewPhraseSearches, $aNewWordsetSearches);
						usort($aNewPhraseSearches, 'bySearchRank');
						$aNewPhraseSearches = array_slice($aNewPhraseSearches, 0, 50);
					}

					// Re-group the searches by their score, junk anything over 20 as just not worth trying
					$aGroupedSearches = array();
					foreach($aNewPhraseSearches as $aSearch)
					{
						if ($aSearch['iSearchRank'] < $iMaxRank)
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
				}
			}
			else
			{
					// Re-group the searches by their score, junk anything over 20 as just not worth trying
					$aGroupedSearches = array();
					foreach($aSearches as $aSearch)
					{
						if ($aSearch['iSearchRank'] < $iMaxRank)
						{
							if (!isset($aGroupedSearches[$aSearch['iSearchRank']])) $aGroupedSearches[$aSearch['iSearchRank']] = array();
							$aGroupedSearches[$aSearch['iSearchRank']][] = $aSearch;
						}
					}
					ksort($aGroupedSearches);
			}
				
				if (CONST_Debug) var_Dump($aGroupedSearches);

				if ($bReverseInPlan)
				{
					foreach($aGroupedSearches as $iGroup => $aSearches)
					{
						foreach($aSearches as $iSearch => $aSearch)
						{
							if (sizeof($aSearch['aAddress']))
							{
								$aReverseSearch = $aSearch;
								$iReverseItem = array_pop($aSearch['aAddress']);
								$aReverseSearch['aName'][$iReverseItem] = $iReverseItem;
								$aGroupedSearches[$iGroup][] = $aReverseSearch;
							}
						}
					}
				}

//var_Dump($aGroupedSearches); exit;

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

				if ($bReverseInPlan)
				{
					foreach($aGroupedSearches as $iGroup => $aSearches)
					{
						foreach($aSearches as $iSearch => $aSearch)
						{
							if (sizeof($aSearch['aAddress']))
							{
								$aReverseSearch = $aSearch;
								$iReverseItem = array_pop($aSearch['aAddress']);
								$aReverseSearch['aName'][$iReverseItem] = $iReverseItem;
								$aGroupedSearches[$iGroup][] = $aReverseSearch;
							}
						}
					}
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

						// Must have a location term
						if (!sizeof($aSearch['aName']) && !sizeof($aSearch['aAddress']) && !$aSearch['fLon'])
						{
							if (!$bBoundingBoxSearch && !$aSearch['fLon']) continue;
							if (!$aSearch['sClass']) continue;
							if (CONST_Debug) var_dump('<hr>',$aSearch);
							if (CONST_Debug) _debugDumpGroupedSearches(array($iGroupedRank => array($aSearch)), $aValidTokens);	

							$sSQL = "select count(*) from pg_tables where tablename = 'place_classtype_".$aSearch['sClass']."_".$aSearch['sType']."'";
							if ($oDB->getOne($sSQL))
							{
								$sSQL = "select place_id from place_classtype_".$aSearch['sClass']."_".$aSearch['sType'];								
								$sSQL .= " where st_contains($sViewboxSmallSQL, centroid)";
								if ($sViewboxCentreSQL)	$sSQL .= " order by st_distance($sViewboxCentreSQL, centroid) asc";
								$sSQL .= " limit $iLimit";
								if (CONST_Debug) var_dump($sSQL);
								$aPlaceIDs = $oDB->getCol($sSQL);

								if (!sizeof($aPlaceIDs))
								{
									$sSQL = "select place_id from place_classtype_".$aSearch['sClass']."_".$aSearch['sType'];								
									$sSQL .= " where st_contains($sViewboxLargeSQL, centroid)";
									if ($sViewboxCentreSQL)	$sSQL .= " order by st_distance($sViewboxCentreSQL, centroid) asc";
									$sSQL .= " limit $iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $oDB->getCol($sSQL);
								}
							}
							else
							{
								$sSQL = "select place_id from placex where class='".$aSearch['sClass']."' and type='".$aSearch['sType']."'";
								$sSQL .= " and st_contains($sViewboxSmallSQL, centroid)";
								if ($sViewboxCentreSQL)	$sSQL .= " order by st_distance($sViewboxCentreSQL, centroid) asc";
								$sSQL .= " limit $iLimit";
								if (CONST_Debug) var_dump($sSQL);
								$aPlaceIDs = $oDB->getCol($sSQL);
							}
						}
						else
						{
							if (CONST_Debug) var_dump('<hr>',$aSearch);
							if (CONST_Debug) _debugDumpGroupedSearches(array($iGroupedRank => array($aSearch)), $aValidTokens);	
							$aPlaceIDs = array();
						
							// First we need a position, either aName or fLat or both
							$aTerms = array();
							$aOrder = array();
							if (sizeof($aSearch['aName'])) $aTerms[] = "name_vector @> ARRAY[".join($aSearch['aName'],",")."]";
							if (sizeof($aSearch['aAddress']) && $aSearch['aName'] != $aSearch['aAddress']) $aTerms[] = "nameaddress_vector @> ARRAY[".join($aSearch['aAddress'],",")."]";
							if ($aSearch['sCountryCode']) $aTerms[] = "country_code = '".pg_escape_string($aSearch['sCountryCode'])."'";
							if ($aSearch['sHouseNumber']) $aTerms[] = "address_rank in (26,27)";
							if ($aSearch['fLon'] && $aSearch['fLat'])
							{
								$aTerms[] = "ST_DWithin(centroid, ST_SetSRID(ST_Point(".$aSearch['fLon'].",".$aSearch['fLat']."),4326), ".$aSearch['fRadius'].")";
								$aOrder[] = "ST_Distance(centroid, ST_SetSRID(ST_Point(".$aSearch['fLon'].",".$aSearch['fLat']."),4326)) ASC";
							}
							if (sizeof($aExcludePlaceIDs))
							{
								$aTerms[] = "place_id not in (".join(',',$aExcludePlaceIDs).")";
							}
							if ($bBoundingBoxSearch) $aTerms[] = "centroid && $sViewboxSmallSQL";
							if ($sNearPointSQL) $aOrder[] = "ST_Distance($sNearPointSQL, centroid) asc";
							if ($sViewboxSmallSQL) $aOrder[] = "ST_Contains($sViewboxSmallSQL, centroid) desc";
							if ($sViewboxLargeSQL) $aOrder[] = "ST_Contains($sViewboxLargeSQL, centroid) desc";
							$aOrder[] = "search_rank ASC";
						
							if (sizeof($aTerms))
							{
								$sSQL = "select place_id";
								if ($sViewboxSmallSQL) $sSQL .= ",ST_Contains($sViewboxSmallSQL, centroid) as in_small";
								else $sSQL .= ",false as in_small";
								if ($sViewboxLargeSQL) $sSQL .= ",ST_Contains($sViewboxLargeSQL, centroid) as in_large";
								else $sSQL .= ",false as in_large";
								$sSQL .= " from search_name";
								$sSQL .= " where ".join(' and ',$aTerms);
								$sSQL .= " order by ".join(', ',$aOrder);
								if ($aSearch['sHouseNumber'])
									$sSQL .= " limit 50";
								elseif (!sizeof($aSearch['aName']) && !sizeof($aSearch['aAddress']) && $aSearch['sClass'])
									$sSQL .= " limit 1";
								else
									$sSQL .= " limit ".$iLimit;

								if (CONST_Debug) var_dump($sSQL);
								$aViewBoxPlaceIDs = $oDB->getAll($sSQL);
								if (PEAR::IsError($aViewBoxPlaceIDs))
								{
									var_dump($sSQL, $aViewBoxPlaceIDs);					
									exit;
								}

								// Did we have an viewbox matches?
								$aPlaceIDs = array();
								$bViewBoxMatch = false;
								foreach($aViewBoxPlaceIDs as $aViewBoxRow)
								{
									if ($bViewBoxMatch == 1 && $aViewBoxRow['in_small'] == 'f') break;
									if ($bViewBoxMatch == 2 && $aViewBoxRow['in_large'] == 'f') break;
									if ($aViewBoxRow['in_small'] == 't') $bViewBoxMatch = 1;
									else if ($aViewBoxRow['in_large'] == 't') $bViewBoxMatch = 2;
									$aPlaceIDs[] = $aViewBoxRow['place_id'];
								}
							}

							if ($aSearch['sHouseNumber'] && sizeof($aPlaceIDs))
							{
								$aRoadPlaceIDs = $aPlaceIDs;
								$sPlaceIDs = join(',',$aPlaceIDs);
	
								// Now they are indexed look for a house attached to a street we found
								$sHouseNumberRegex = '\\\\m'.str_replace(' ','[-, ]',$aSearch['sHouseNumber']).'\\\\M';						
								$sSQL = "select place_id from placex where parent_place_id in (".$sPlaceIDs.") and housenumber ~* E'".$sHouseNumberRegex."'";
								if (sizeof($aExcludePlaceIDs))
								{
									$sSQL .= " and place_id not in (".join(',',$aExcludePlaceIDs).")";
								}
								$sSQL .= " limit $iLimit";
								if (CONST_Debug) var_dump($sSQL);
								$aPlaceIDs = $oDB->getCol($sSQL);

								// If not try the tiger fallback table
								if (!sizeof($aPlaceIDs))
								{
									$sSQL = "select place_id from location_property_tiger where parent_place_id in (".$sPlaceIDs.") and housenumber = '".pg_escape_string($aSearch['sHouseNumber'])."'";
									if (sizeof($aExcludePlaceIDs))
									{
										$sSQL .= " and place_id not in (".join(',',$aExcludePlaceIDs).")";
									}
//									$sSQL .= " limit $iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $oDB->getCol($sSQL);
								}

								// Fallback to the road
								if (!sizeof($aPlaceIDs))
								{
									$aPlaceIDs = $aRoadPlaceIDs;
								}
								
							}
						
							if ($aSearch['sClass'] && sizeof($aPlaceIDs))
							{
								$sPlaceIDs = join(',',$aPlaceIDs);

								if (!$aSearch['sOperator'] || $aSearch['sOperator'] == 'name')
								{
									// If they were searching for a named class (i.e. 'Kings Head pub') then we might have an extra match
									$sSQL = "select place_id from placex where place_id in ($sPlaceIDs) and class='".$aSearch['sClass']."' and type='".$aSearch['sType']."'";
									$sSQL .= " order by rank_search asc limit $iLimit";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $oDB->getCol($sSQL);
								}
								
								if (!$aSearch['sOperator'] || $aSearch['sOperator'] == 'near') // & in
								{
									$sSQL = "select rank_search from placex where place_id in ($sPlaceIDs) order by rank_search asc limit 1";
									if (CONST_Debug) var_dump($sSQL);
									$iMaxRank = ((int)$oDB->getOne($sSQL)) + 5;

									$sSQL = "select place_id from placex where place_id in ($sPlaceIDs) and rank_search < $iMaxRank";
									if (CONST_Debug) var_dump($sSQL);
									$aPlaceIDs = $oDB->getCol($sSQL);
									$sPlaceIDs = join(',',$aPlaceIDs);

									$fRange = 0.01;
									$sSQL = "select count(*) from pg_tables where tablename = 'place_classtype_".$aSearch['sClass']."_".$aSearch['sType']."'";
									if ($oDB->getOne($sSQL))
									{
										// More efficient - can make the range bigger
  									$fRange = 0.05;
										$sSQL = "select l.place_id from place_classtype_".$aSearch['sClass']."_".$aSearch['sType']." as l";
										$sSQL .= ",placex as f where ";
										$sSQL .= "f.place_id in ($sPlaceIDs) and ST_DWithin(l.centroid, st_centroid(f.geometry), $fRange) ";
										if (sizeof($aExcludePlaceIDs))
										{
											$sSQL .= " and l.place_id not in (".join(',',$aExcludePlaceIDs).")";
										}
										if ($sNearPointSQL) $sSQL .= " order by ST_Distance($sNearPointSQL, l.geometry) ASC";
										else $sSQL .= " order by ST_Distance(l.centroid, f.geometry) asc";
										$sSQL .= " limit $iLimit";
										if (CONST_Debug) var_dump($sSQL);
										$aPlaceIDs = $oDB->getCol($sSQL);
									}
									else
									{
										if (isset($aSearch['fRadius']) && $aSearch['fRadius']) $fRange = $aSearch['fRadius'];
										$sSQL = "select l.place_id from placex as l,placex as f where ";
										$sSQL .= "f.place_id in ($sPlaceIDs) and ST_DWithin(l.geometry, st_centroid(f.geometry), $fRange) ";
										$sSQL .= "and l.class='".$aSearch['sClass']."' and l.type='".$aSearch['sType']."' ";
										if (sizeof($aExcludePlaceIDs))
										{
											$sSQL .= " and l.place_id not in (".join(',',$aExcludePlaceIDs).")";
										}
										if ($sNearPointSQL) $sSQL .= " order by ST_Distance($sNearPointSQL, l.geometry) ASC";
										else $sSQL .= " order by ST_Distance(l.geometry, f.geometry) asc, l.rank_search ASC";
										$sSQL .= " limit $iLimit";
										if (CONST_Debug) var_dump($sSQL);
										$aPlaceIDs = $oDB->getCol($sSQL);
									}
								}
							}
						
						}

						if (PEAR::IsError($aPlaceIDs))
						{
							var_dump($sSQL, $aPlaceIDs);					
							exit;
						}

						if (CONST_Debug) var_Dump($aPlaceIDs);

						foreach($aPlaceIDs as $iPlaceID)
						{
							$aResultPlaceIDs[$iPlaceID] = $iPlaceID;
						}
						if ($iQueryLoop > 20) break;
					}
					//exit;
					if (sizeof($aResultPlaceIDs)) break;
					if ($iGroupLoop > 4) break;
					if ($iQueryLoop > 30) break;
				}
//exit;
				// Did we find anything?	
				if (sizeof($aResultPlaceIDs))
				{
//var_Dump($aResultPlaceIDs);exit;
					// Get the details for display (is this a redundant extra step?)
					$sPlaceIDs = join(',',$aResultPlaceIDs);
					$sOrderSQL = 'CASE ';
					foreach(array_keys($aResultPlaceIDs) as $iOrder => $iPlaceID)
					{
						$sOrderSQL .= 'when min(place_id) = '.$iPlaceID.' then '.$iOrder.' ';
					}
					$sOrderSQL .= ' ELSE 10000000 END';
					$sSQL = "select osm_type,osm_id,class,type,rank_search,rank_address,min(place_id) as place_id,country_code,";
					$sSQL .= "get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
					$sSQL .= "get_name_by_language(name, $sLanguagePrefArraySQL) as placename,";
					$sSQL .= "get_name_by_language(name, ARRAY['ref']) as ref,";
					$sSQL .= "avg(ST_X(ST_Centroid(geometry))) as lon,avg(ST_Y(ST_Centroid(geometry))) as lat, ";
					$sSQL .= $sOrderSQL." as porder ";
					$sSQL .= "from placex where place_id in ($sPlaceIDs) ";
					$sSQL .= "group by osm_type,osm_id,class,type,rank_search,rank_address,country_code";
					if (!$bDeDupe) $sSQL .= ",place_id";
					$sSQL .= ",get_address_by_language(place_id, $sLanguagePrefArraySQL) ";
					$sSQL .= ",get_name_by_language(name, $sLanguagePrefArraySQL) ";
					$sSQL .= ",get_name_by_language(name, ARRAY['ref']) ";
					$sSQL .= " union ";
					$sSQL .= "select 'T' as osm_type,place_id as osm_id,'place' as class,'house' as type,30 as rank_search,30 as rank_address,min(place_id) as place_id,'us' as country_code,";
					$sSQL .= "get_tiger_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
					$sSQL .= "null as placename,";
					$sSQL .= "null as ref,";
					$sSQL .= "avg(ST_X(centroid)) as lon,avg(ST_Y(centroid)) as lat, ";
					$sSQL .= $sOrderSQL." as porder ";
					$sSQL .= "from location_property_tiger where place_id in ($sPlaceIDs) ";
					$sSQL .= "group by place_id";
					if (!$bDeDupe) $sSQL .= ",place_id";
					$sSQL .= ",get_tiger_address_by_language(place_id, $sLanguagePrefArraySQL) ";
					$sSQL .= "order by rank_search,rank_address,porder asc";
					if (CONST_Debug) var_dump('<hr>',$sSQL);
					$aSearchResults = $oDB->getAll($sSQL);
//var_dump($sSQL,$aSearchResults);exit;

					if (PEAR::IsError($aSearchResults))
					{
						var_dump($sSQL, $aSearchResults);					
						exit;
					}
				}
			}
		}
	
	$sSearchResult = '';
	if (!sizeof($aSearchResults) && isset($_GET['q']) && $_GET['q'])
	{
		$sSearchResult = 'No Results Found';
	}
	
	$aClassType = getClassTypesWithImportance();

	foreach($aSearchResults as $iResNum => $aResult)
	{
		if (CONST_Search_AreaPolygons || true)
		{
			// Get the bounding box and outline polygon
			$sSQL = "select place_id,numfeatures,area,outline,";
			$sSQL .= "ST_Y(ST_PointN(ExteriorRing(ST_Box2D(outline)),4)) as minlat,ST_Y(ST_PointN(ExteriorRing(ST_Box2D(outline)),2)) as maxlat,";
			$sSQL .= "ST_X(ST_PointN(ExteriorRing(ST_Box2D(outline)),1)) as minlon,ST_X(ST_PointN(ExteriorRing(ST_Box2D(outline)),3)) as maxlon,";
			$sSQL .= "ST_AsText(outline) as outlinestring from get_place_boundingbox_quick(".$aResult['place_id'].")";
			$aPointPolygon = $oDB->getRow($sSQL);
			if (PEAR::IsError($aPointPolygon))
			{
				var_dump($sSQL, $aPointPolygon);
				exit;
			}
			if ($aPointPolygon['place_id'])
			{
				// Translate geometary string to point array
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

				// Output data suitable for display (points and a bounding box)
				if ($bShowPolygons)
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
			if ($bShowPolygons)
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

		if ($bShowAddressDetails)
		{
			$aResult['address'] = getAddressDetails($oDB, $sLanguagePrefArraySQL, $aResult['place_id'], $aResult['country_code']);
//var_dump($aResult['address']);
//exit;
		}

		if (isset($aClassType[$aResult['class'].':'.$aResult['type']]['importance']) 
			&& $aClassType[$aResult['class'].':'.$aResult['type']]['importance'])
		{
			$aResult['importance'] = $aClassType[$aResult['class'].':'.$aResult['type']]['importance'];
		}
		else
		{
			$aResult['importance'] = 1000000000000000;
		}

		$aResult['name'] = $aResult['langaddress'];
		$aResult['foundorder'] = $iResNum;
		$aSearchResults[$iResNum] = $aResult;
	}

//var_dump($aSearchResults);exit;
	
	uasort($aSearchResults, 'byImportance');
	
	$aOSMIDDone = array();
	$aClassTypeNameDone = array();
	$aToFilter = $aSearchResults;
	$aSearchResults = array();

	$bFirst = true;
	foreach($aToFilter as $iResNum => $aResult)
	{
		if ($aResult['type'] == 'adminitrative') $aResult['type'] = 'administrative';
		$aExcludePlaceIDs[$aResult['place_id']] = $aResult['place_id'];
		if ($bFirst)
		{
			$fLat = $aResult['lat'];
			$fLon = $aResult['lon'];
			if (isset($aResult['zoom'])) $iZoom = $aResult['zoom'];
			$bFirst = false;
		}
		if (!$bDeDupe || (!isset($aOSMIDDone[$aResult['osm_type'].$aResult['osm_id']])
			&& !isset($aClassTypeNameDone[$aResult['osm_type'].$aResult['osm_class'].$aResult['name']])))
		{
			$aOSMIDDone[$aResult['osm_type'].$aResult['osm_id']] = true;
			$aClassTypeNameDone[$aResult['osm_type'].$aResult['osm_class'].$aResult['name']] = true;
			$aSearchResults[] = $aResult;
		}
	}

	$sDataDate = $oDB->getOne("select TO_CHAR(lastimportdate - '1 day'::interval,'YYYY/MM/DD') from import_status limit 1");

	if (isset($_GET['nearlat']) && isset($_GET['nearlon']))
	{
		$sQuery .= ' ['.$_GET['nearlat'].','.$_GET['nearlon'].']';
	}

	if ($sQuery)
	{
		logEnd($oDB, $hLog, sizeof($aToFilter));
	}
 	$sMoreURL = CONST_Website_BaseURL.'search?format='.urlencode($sOutputFormat).'&exclude_place_ids='.join(',',$aExcludePlaceIDs);
	$sMoreURL .= '&accept-language='.$_SERVER["HTTP_ACCEPT_LANGUAGE"];
	if ($bShowPolygons) $sMoreURL .= '&polygon=1';
	if ($bShowAddressDetails) $sMoreURL .= '&addressdetails=1';
	if (isset($_GET['viewbox']) && $_GET['viewbox']) $sMoreURL .= '&viewbox='.urlencode($_GET['viewbox']);
	if (isset($_GET['nearlat']) && isset($_GET['nearlon'])) $sMoreURL .= '&nearlat='.(float)$_GET['nearlat'].'&nearlon='.(float)$_GET['nearlon'];
	if ($sSuggestion)
	{
		$sSuggestionURL = $sMoreURL.'&q='.urlencode($sSuggestion);
	}
	$sMoreURL .= '&q='.urlencode($sQuery);

	if (CONST_Debug) exit;

	include(CONST_BasePath.'/lib/template/search-'.$sOutputFormat.'.php');

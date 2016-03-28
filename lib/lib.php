<?php

	function failInternalError($sError, $sSQL = false, $vDumpVar = false)
	{
		header('HTTP/1.0 500 Internal Server Error');
		header('Content-type: text/html; charset=utf-8');
		echo "<html><body><h1>Internal Server Error</h1>";
		echo '<p>Nominatim has encountered an internal error while processing your request. This is most likely because of a bug in the software.</p>';
		echo "<p><b>Details:</b> ".$sError,"</p>";
		echo '<p>Feel free to report the bug in the <a href="http://trac.openstreetmap.org">OSM bug database</a>. Please include the error message above and the URL you used.</p>';
		if (CONST_Debug)
		{
			echo "<hr><h2>Debugging Information</h2><br>";
			if ($sSQL)
			{
				echo "<h3>SQL query</h3><code>".$sSQL."</code>";
			}
			if ($vDumpVar)
			{
				echo "<h3>Result</h3> <code>";
				var_dump($vDumpVar);
				echo "</code>";
			}
		}
		echo "\n</body></html>\n";
		exit;
	}


	function userError($sError)
	{
		header('HTTP/1.0 400 Bad Request');
		header('Content-type: text/html; charset=utf-8');
		echo "<html><body><h1>Bad Request</h1>";
		echo '<p>Nominatim has encountered an error with your request.</p>';
		echo "<p><b>Details:</b> ".$sError,"</p>";
		echo '<p>If you feel this error is incorrect feel free to report the bug in the <a href="http://trac.openstreetmap.org">OSM bug database</a>. Please include the error message above and the URL you used.</p>';
		echo "\n</body></html>\n";
		exit;
	}

	function getParamBool($name, $default=false)
	{
		if (!isset($_GET[$name])) return $default;

		return (bool) $_GET[$name];
	}

	function fail($sError, $sUserError = false)
	{
		if (!$sUserError) $sUserError = $sError;
		error_log('ERROR: '.$sError);
		echo $sUserError."\n";
		exit(-1);
	}


	function getBlockingProcesses()
	{
		$sStats = file_get_contents('/proc/stat');
		if (preg_match('/procs_blocked ([0-9]+)/i', $sStats, $aMatches))
		{
			return (int)$aMatches[1];
		}
		return 0;
	}


	function getLoadAverage()
	{
		$sLoadAverage = file_get_contents('/proc/loadavg');
		$aLoadAverage = explode(' ',$sLoadAverage);
		return (float)$aLoadAverage[0];
	}


	function getProcessorCount()
	{
		$sCPU = file_get_contents('/proc/cpuinfo');
		preg_match_all('#processor\s+: [0-9]+#', $sCPU, $aMatches);
		return sizeof($aMatches[0]);
	}


	function getTotalMemoryMB()
	{
		$sCPU = file_get_contents('/proc/meminfo');
		preg_match('#MemTotal: +([0-9]+) kB#', $sCPU, $aMatches);
		return (int)($aMatches[1]/1024);
	}


	function getCacheMemoryMB()
	{
		$sCPU = file_get_contents('/proc/meminfo');
		preg_match('#Cached: +([0-9]+) kB#', $sCPU, $aMatches);
		return (int)($aMatches[1]/1024);
	}


	function bySearchRank($a, $b)
	{
		if ($a['iSearchRank'] == $b['iSearchRank'])
			return strlen($a['sOperator']) + strlen($a['sHouseNumber']) - strlen($b['sOperator']) - strlen($b['sHouseNumber']);
		return ($a['iSearchRank'] < $b['iSearchRank']?-1:1);
	}


	function byImportance($a, $b)
	{
		if ($a['importance'] != $b['importance'])
			return ($a['importance'] > $b['importance']?-1:1);
		/*
		   if ($a['aPointPolygon']['numfeatures'] != $b['aPointPolygon']['numfeatures'])
		   return ($a['aPointPolygon']['numfeatures'] > $b['aPointPolygon']['numfeatures']?-1:1);
		   if ($a['aPointPolygon']['area'] != $b['aPointPolygon']['area'])
		   return ($a['aPointPolygon']['area'] > $b['aPointPolygon']['area']?-1:1);
		//      if ($a['levenshtein'] != $b['levenshtein'])
		//          return ($a['levenshtein'] < $b['levenshtein']?-1:1);
		if ($a['rank_search'] != $b['rank_search'])
		return ($a['rank_search'] < $b['rank_search']?-1:1);
		 */
		return ($a['foundorder'] < $b['foundorder']?-1:1);
	}


	function getPreferredLanguages($sLangString=false)
	{
		if (!$sLangString)
		{
			// If we have been provided the value in $_GET it overrides browser value
			if (isset($_GET['accept-language']) && $_GET['accept-language'])
			{
				$_SERVER["HTTP_ACCEPT_LANGUAGE"] = $_GET['accept-language'];
				$sLangString = $_GET['accept-language'];
			}
			else if (isset($_SERVER["HTTP_ACCEPT_LANGUAGE"]))
			{
				$sLangString = $_SERVER["HTTP_ACCEPT_LANGUAGE"];
			}
		}

		$aLanguages = array();
		if ($sLangString)
		{
			if (preg_match_all('/(([a-z]{1,8})(-[a-z]{1,8})?)\s*(;\s*q\s*=\s*(1|0\.[0-9]+))?/i', $sLangString, $aLanguagesParse, PREG_SET_ORDER))
			{
				foreach($aLanguagesParse as $iLang => $aLanguage)
				{
					$aLanguages[$aLanguage[1]] = isset($aLanguage[5])?(float)$aLanguage[5]:1 - ($iLang/100);
					if (!isset($aLanguages[$aLanguage[2]])) $aLanguages[$aLanguage[2]] = $aLanguages[$aLanguage[1]]/10;
				}
				arsort($aLanguages);
			}
		}
		if (!sizeof($aLanguages) && CONST_Default_Language) $aLanguages = array(CONST_Default_Language=>1);
		foreach($aLanguages as $sLangauge => $fLangauagePref)
		{
			$aLangPrefOrder['short_name:'.$sLangauge] = 'short_name:'.$sLangauge;
		}
		foreach($aLanguages as $sLangauge => $fLangauagePref)
		{
			$aLangPrefOrder['name:'.$sLangauge] = 'name:'.$sLangauge;
		}
		foreach($aLanguages as $sLangauge => $fLangauagePref)
		{
			$aLangPrefOrder['place_name:'.$sLangauge] = 'place_name:'.$sLangauge;
		}
		foreach($aLanguages as $sLangauge => $fLangauagePref)
		{
			$aLangPrefOrder['official_name:'.$sLangauge] = 'official_name:'.$sLangauge;
		}
		$aLangPrefOrder['short_name'] = 'short_name';
		$aLangPrefOrder['name'] = 'name';
		$aLangPrefOrder['place_name'] = 'place_name';
		$aLangPrefOrder['official_name'] = 'official_name';
		$aLangPrefOrder['ref'] = 'ref';
		$aLangPrefOrder['type'] = 'type';
		return $aLangPrefOrder;
	}


	function getWordSets($aWords, $iDepth)
	{
		$aResult = array(array(join(' ',$aWords)));
		$sFirstToken = '';
		if ($iDepth < 8) {
			while(sizeof($aWords) > 1)
			{
				$sWord = array_shift($aWords);
				$sFirstToken .= ($sFirstToken?' ':'').$sWord;
				$aRest = getWordSets($aWords, $iDepth+1);
				foreach($aRest as $aSet)
				{
					$aResult[] = array_merge(array($sFirstToken),$aSet);
				}
			}
		}
		return $aResult;
	}

	function getInverseWordSets($aWords, $iDepth)
	{
		$aResult = array(array(join(' ',$aWords)));
		$sFirstToken = '';
		if ($iDepth < 8)
		{
			while(sizeof($aWords) > 1)
			{
				$sWord = array_pop($aWords);
				$sFirstToken = $sWord.($sFirstToken?' ':'').$sFirstToken;
				$aRest = getInverseWordSets($aWords, $iDepth+1);
				foreach($aRest as $aSet)
				{
					$aResult[] = array_merge(array($sFirstToken),$aSet);
				}
			}
		}
		return $aResult;
	}


	function getTokensFromSets($aSets)
	{
		$aTokens = array();
		foreach($aSets as $aSet)
		{
			foreach($aSet as $sWord)
			{
				$aTokens[' '.$sWord] = ' '.$sWord;
				$aTokens[$sWord] = $sWord;
				//if (!strpos($sWord,' ')) $aTokens[$sWord] = $sWord;
			}
		}
		return $aTokens;
	}


	/*
	   GB Postcode functions
	 */

	function gbPostcodeAlphaDifference($s1, $s2)
	{
		$aValues = array(
				'A'=>0,
				'B'=>1,
				'D'=>2,
				'E'=>3,
				'F'=>4,
				'G'=>5,
				'H'=>6,
				'J'=>7,
				'L'=>8,
				'N'=>9,
				'O'=>10,
				'P'=>11,
				'Q'=>12,
				'R'=>13,
				'S'=>14,
				'T'=>15,
				'U'=>16,
				'W'=>17,
				'X'=>18,
				'Y'=>19,
				'Z'=>20);
		return abs(($aValues[$s1[0]]*21+$aValues[$s1[1]]) - ($aValues[$s2[0]]*21+$aValues[$s2[1]]));
	}


	function gbPostcodeCalculate($sPostcode, $sPostcodeSector, $sPostcodeEnd, &$oDB)
	{
		// Try an exact match on the gb_postcode table
		$sSQL = 'select \'AA\', ST_X(ST_Centroid(geometry)) as lon,ST_Y(ST_Centroid(geometry)) as lat from gb_postcode where postcode = \''.$sPostcode.'\'';
		$aNearPostcodes = $oDB->getAll($sSQL);
		if (PEAR::IsError($aNearPostcodes))
		{
			var_dump($sSQL, $aNearPostcodes);
			exit;
		}

		if (sizeof($aNearPostcodes))
		{
			$aPostcodes = array();
			foreach($aNearPostcodes as $aPostcode)
			{
				$aPostcodes[] = array('lat' => $aPostcode['lat'], 'lon' => $aPostcode['lon'], 'radius' => 0.005);
			}

			return $aPostcodes;
		}

		return false;
	}


	function usPostcodeCalculate($sPostcode, &$oDB)
	{
		$iZipcode = (int)$sPostcode;

		// Try an exact match on the us_zippostcode table
		$sSQL = 'select zipcode, ST_X(ST_Centroid(geometry)) as lon,ST_Y(ST_Centroid(geometry)) as lat from us_zipcode where zipcode = '.$iZipcode;
		$aNearPostcodes = $oDB->getAll($sSQL);
		if (PEAR::IsError($aNearPostcodes))
		{
			var_dump($sSQL, $aNearPostcodes);
			exit;
		}

		if (!sizeof($aNearPostcodes))
		{
			$sSQL = 'select zipcode,ST_X(ST_Centroid(geometry)) as lon,ST_Y(ST_Centroid(geometry)) as lat from us_zipcode where zipcode between '.($iZipcode-100).' and '.($iZipcode+100).' order by abs(zipcode - '.$iZipcode.') asc limit 5';
			$aNearPostcodes = $oDB->getAll($sSQL);
			if (PEAR::IsError($aNearPostcodes))
			{
				var_dump($sSQL, $aNearPostcodes);
				exit;
			}
		}

		if (!sizeof($aNearPostcodes))
		{
			return false;
		}

		$fTotalLat = 0;
		$fTotalLon = 0;
		$fTotalFac = 0;
		foreach($aNearPostcodes as $aPostcode)
		{
			$iDiff = abs($aPostcode['zipcode'] - $iZipcode) + 1;
			if ($iDiff == 0)
				$fFac = 1;
			else
				$fFac = 1/($iDiff*$iDiff);

			$fTotalFac += $fFac;
			$fTotalLat += $aPostcode['lat'] * $fFac;
			$fTotalLon += $aPostcode['lon'] * $fFac;
		}
		if ($fTotalFac)
		{
			$fLat = $fTotalLat / $fTotalFac;
			$fLon = $fTotalLon / $fTotalFac;
			return array(array('lat' => $fLat, 'lon' => $fLon, 'radius' => 0.2));
		}
		return false;

		/*
		   $fTotalFac is a surprisingly good indicator of accuracy
		   $iZoom = 18 + round(log($fTotalFac,32));
		   $iZoom = max(13,min(18,$iZoom));
		 */
	}


	function getClassTypes()
	{
		return array(
 'boundary:administrative:1' => array('label'=>'Continent','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'boundary:administrative:2' => array('label'=>'Country','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'place:country' => array('label'=>'Country','frequency'=>0,'icon'=>'poi_boundary_administrative','defzoom'=>6, 'defdiameter' => 15,),
 'boundary:administrative:3' => array('label'=>'State','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'boundary:administrative:4' => array('label'=>'State','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'place:state' => array('label'=>'State','frequency'=>0,'icon'=>'poi_boundary_administrative','defzoom'=>8, 'defdiameter' => 5.12,),
 'boundary:administrative:5' => array('label'=>'State District','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'boundary:administrative:6' => array('label'=>'County','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'boundary:administrative:7' => array('label'=>'County','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'place:county' => array('label'=>'County','frequency'=>108,'icon'=>'poi_boundary_administrative','defzoom'=>10, 'defdiameter' => 1.28,),
 'boundary:administrative:8' => array('label'=>'City','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'place:city' => array('label'=>'City','frequency'=>66,'icon'=>'poi_place_city','defzoom'=>12, 'defdiameter' => 0.32,),
 'boundary:administrative:9' => array('label'=>'City District','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'boundary:administrative:10' => array('label'=>'Suburb','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'boundary:administrative:11' => array('label'=>'Neighbourhood','frequency'=>0,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'place:region' => array('label'=>'Region','frequency'=>0,'icon'=>'poi_boundary_administrative','defzoom'=>8, 'defdiameter' => 0.04,),
 'place:island' => array('label'=>'Island','frequency'=>288,'icon'=>'','defzoom'=>11, 'defdiameter' => 0.64,),
 'boundary:administrative' => array('label'=>'Administrative','frequency'=>413,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'boundary:postal_code' => array('label'=>'Postcode','frequency'=>413,'icon'=>'poi_boundary_administrative', 'defdiameter' => 0.32,),
 'place:town' => array('label'=>'Town','frequency'=>1497,'icon'=>'poi_place_town','defzoom'=>14, 'defdiameter' => 0.08,),
 'place:village' => array('label'=>'Village','frequency'=>11230,'icon'=>'poi_place_village','defzoom'=>15, 'defdiameter' => 0.04,),
 'place:hamlet' => array('label'=>'Hamlet','frequency'=>7075,'icon'=>'poi_place_village','defzoom'=>15, 'defdiameter' => 0.04,),
 'place:suburb' => array('label'=>'Suburb','frequency'=>2528,'icon'=>'poi_place_village', 'defdiameter' => 0.04,),
 'place:locality' => array('label'=>'Locality','frequency'=>4113,'icon'=>'poi_place_village', 'defdiameter' => 0.02,),
 'landuse:farm' => array('label'=>'Farm','frequency'=>1201,'icon'=>'', 'defdiameter' => 0.02,),
 'place:farm' => array('label'=>'Farm','frequency'=>1162,'icon'=>'', 'defdiameter' => 0.02,),

 'highway:motorway_junction' => array('label'=>'Motorway Junction','frequency'=>1126,'icon'=>'','simplelabel'=>'Junction',),
 'highway:motorway' => array('label'=>'Motorway','frequency'=>4627,'icon'=>'','simplelabel'=>'Road',),
 'highway:trunk' => array('label'=>'Trunk','frequency'=>23084,'icon'=>'','simplelabel'=>'Road',),
 'highway:primary' => array('label'=>'Primary','frequency'=>32138,'icon'=>'','simplelabel'=>'Road',),
 'highway:secondary' => array('label'=>'Secondary','frequency'=>25807,'icon'=>'','simplelabel'=>'Road',),
 'highway:tertiary' => array('label'=>'Tertiary','frequency'=>29829,'icon'=>'','simplelabel'=>'Road',),
 'highway:residential' => array('label'=>'Residential','frequency'=>361498,'icon'=>'','simplelabel'=>'Road',),
 'highway:unclassified' => array('label'=>'Unclassified','frequency'=>66441,'icon'=>'','simplelabel'=>'Road',),
 'highway:living_street' => array('label'=>'Living Street','frequency'=>710,'icon'=>'','simplelabel'=>'Road',),
 'highway:service' => array('label'=>'Service','frequency'=>9963,'icon'=>'','simplelabel'=>'Road',),
 'highway:track' => array('label'=>'Track','frequency'=>2565,'icon'=>'','simplelabel'=>'Road',),
 'highway:road' => array('label'=>'Road','frequency'=>591,'icon'=>'','simplelabel'=>'Road',),
 'highway:byway' => array('label'=>'Byway','frequency'=>346,'icon'=>'','simplelabel'=>'Road',),
 'highway:bridleway' => array('label'=>'Bridleway','frequency'=>1556,'icon'=>'',),
 'highway:cycleway' => array('label'=>'Cycleway','frequency'=>2419,'icon'=>'',),
 'highway:pedestrian' => array('label'=>'Pedestrian','frequency'=>2757,'icon'=>'',),
 'highway:footway' => array('label'=>'Footway','frequency'=>15008,'icon'=>'',),
 'highway:steps' => array('label'=>'Steps','frequency'=>444,'icon'=>'','simplelabel'=>'Footway',),
 'highway:motorway_link' => array('label'=>'Motorway Link','frequency'=>795,'icon'=>'','simplelabel'=>'Road',),
 'highway:trunk_link' => array('label'=>'Trunk Link','frequency'=>1258,'icon'=>'','simplelabel'=>'Road',),
 'highway:primary_link' => array('label'=>'Primary Link','frequency'=>313,'icon'=>'','simplelabel'=>'Road',),

 'landuse:industrial' => array('label'=>'Industrial','frequency'=>1062,'icon'=>'',),
 'landuse:residential' => array('label'=>'Residential','frequency'=>886,'icon'=>'',),
 'landuse:retail' => array('label'=>'Retail','frequency'=>754,'icon'=>'',),
 'landuse:commercial' => array('label'=>'Commercial','frequency'=>657,'icon'=>'',),

 'place:airport' => array('label'=>'Airport','frequency'=>36,'icon'=>'transport_airport2', 'defdiameter' => 0.03,),
 'aeroway:aerodrome' => array('label'=>'Aerodrome','frequency'=>36,'icon'=>'transport_airport2', 'defdiameter' => 0.03,),
 'aeroway' => array('label'=>'Aeroway','frequency'=>36,'icon'=>'transport_airport2', 'defdiameter' => 0.03,),
 'railway:station' => array('label'=>'Station','frequency'=>3431,'icon'=>'transport_train_station2', 'defdiameter' => 0.01,),
 'amenity:place_of_worship' => array('label'=>'Place Of Worship','frequency'=>9049,'icon'=>'place_of_worship_unknown3',),
 'amenity:pub' => array('label'=>'Pub','frequency'=>18969,'icon'=>'food_pub',),
 'amenity:bar' => array('label'=>'Bar','frequency'=>164,'icon'=>'food_bar',),
 'amenity:university' => array('label'=>'University','frequency'=>607,'icon'=>'education_university',),
 'tourism:museum' => array('label'=>'Museum','frequency'=>543,'icon'=>'tourist_museum',),
 'amenity:arts_centre' => array('label'=>'Arts Centre','frequency'=>136,'icon'=>'tourist_art_gallery2',),
 'tourism:zoo' => array('label'=>'Zoo','frequency'=>47,'icon'=>'tourist_zoo',),
 'tourism:theme_park' => array('label'=>'Theme Park','frequency'=>24,'icon'=>'poi_point_of_interest',),
 'tourism:attraction' => array('label'=>'Attraction','frequency'=>1463,'icon'=>'poi_point_of_interest',),
 'leisure:golf_course' => array('label'=>'Golf Course','frequency'=>712,'icon'=>'sport_golf',),
 'historic:castle' => array('label'=>'Castle','frequency'=>316,'icon'=>'tourist_castle',),
 'amenity:hospital' => array('label'=>'Hospital','frequency'=>879,'icon'=>'health_hospital',),
 'amenity:school' => array('label'=>'School','frequency'=>8192,'icon'=>'education_school',),
 'amenity:theatre' => array('label'=>'Theatre','frequency'=>371,'icon'=>'tourist_theatre',),
 'amenity:public_building' => array('label'=>'Public Building','frequency'=>985,'icon'=>'',),
 'amenity:library' => array('label'=>'Library','frequency'=>794,'icon'=>'amenity_library',),
 'amenity:townhall' => array('label'=>'Townhall','frequency'=>242,'icon'=>'',),
 'amenity:community_centre' => array('label'=>'Community Centre','frequency'=>157,'icon'=>'',),
 'amenity:fire_station' => array('label'=>'Fire Station','frequency'=>221,'icon'=>'amenity_firestation3',),
 'amenity:police' => array('label'=>'Police','frequency'=>334,'icon'=>'amenity_police2',),
 'amenity:bank' => array('label'=>'Bank','frequency'=>1248,'icon'=>'money_bank2',),
 'amenity:post_office' => array('label'=>'Post Office','frequency'=>859,'icon'=>'amenity_post_office',),
 'leisure:park' => array('label'=>'Park','frequency'=>2378,'icon'=>'',),
 'amenity:park' => array('label'=>'Park','frequency'=>53,'icon'=>'',),
 'landuse:park' => array('label'=>'Park','frequency'=>50,'icon'=>'',),
 'landuse:recreation_ground' => array('label'=>'Recreation Ground','frequency'=>517,'icon'=>'',),
 'tourism:hotel' => array('label'=>'Hotel','frequency'=>2150,'icon'=>'accommodation_hotel2',),
 'tourism:motel' => array('label'=>'Motel','frequency'=>43,'icon'=>'',),
 'amenity:cinema' => array('label'=>'Cinema','frequency'=>277,'icon'=>'tourist_cinema',),
 'tourism:artwork' => array('label'=>'Artwork','frequency'=>171,'icon'=>'tourist_art_gallery2',),
 'historic:archaeological_site' => array('label'=>'Archaeological Site','frequency'=>407,'icon'=>'tourist_archaeological2',),
 'amenity:doctors' => array('label'=>'Doctors','frequency'=>581,'icon'=>'health_doctors',),
 'leisure:sports_centre' => array('label'=>'Sports Centre','frequency'=>767,'icon'=>'sport_leisure_centre',),
 'leisure:swimming_pool' => array('label'=>'Swimming Pool','frequency'=>24,'icon'=>'sport_swimming_outdoor',),
 'shop:supermarket' => array('label'=>'Supermarket','frequency'=>2673,'icon'=>'shopping_supermarket',),
 'shop:convenience' => array('label'=>'Convenience','frequency'=>1469,'icon'=>'shopping_convenience',),
 'amenity:restaurant' => array('label'=>'Restaurant','frequency'=>3179,'icon'=>'food_restaurant',),
 'amenity:fast_food' => array('label'=>'Fast Food','frequency'=>2289,'icon'=>'food_fastfood',),
 'amenity:cafe' => array('label'=>'Cafe','frequency'=>1780,'icon'=>'food_cafe',),
 'tourism:guest_house' => array('label'=>'Guest House','frequency'=>223,'icon'=>'accommodation_bed_and_breakfast',),
 'amenity:pharmacy' => array('label'=>'Pharmacy','frequency'=>733,'icon'=>'health_pharmacy_dispensing',),
 'amenity:fuel' => array('label'=>'Fuel','frequency'=>1308,'icon'=>'transport_fuel',),
 'natural:peak' => array('label'=>'Peak','frequency'=>3212,'icon'=>'poi_peak',),
 'waterway:waterfall' => array('label'=>'Waterfall','frequency'=>24,'icon'=>'',),
 'natural:wood' => array('label'=>'Wood','frequency'=>1845,'icon'=>'landuse_coniferous_and_deciduous',),
 'natural:water' => array('label'=>'Water','frequency'=>1790,'icon'=>'',),
 'landuse:forest' => array('label'=>'Forest','frequency'=>467,'icon'=>'',),
 'landuse:cemetery' => array('label'=>'Cemetery','frequency'=>463,'icon'=>'',),
 'landuse:allotments' => array('label'=>'Allotments','frequency'=>408,'icon'=>'',),
 'landuse:farmyard' => array('label'=>'Farmyard','frequency'=>397,'icon'=>'',),
 'railway:rail' => array('label'=>'Rail','frequency'=>4894,'icon'=>'',),
 'waterway:canal' => array('label'=>'Canal','frequency'=>1723,'icon'=>'',),
 'waterway:river' => array('label'=>'River','frequency'=>4089,'icon'=>'',),
 'waterway:stream' => array('label'=>'Stream','frequency'=>2684,'icon'=>'',),
 'shop:bicycle' => array('label'=>'Bicycle','frequency'=>349,'icon'=>'shopping_bicycle',),
 'shop:clothes' => array('label'=>'Clothes','frequency'=>315,'icon'=>'shopping_clothes',),
 'shop:hairdresser' => array('label'=>'Hairdresser','frequency'=>312,'icon'=>'shopping_hairdresser',),
 'shop:doityourself' => array('label'=>'Doityourself','frequency'=>247,'icon'=>'shopping_diy',),
 'shop:estate_agent' => array('label'=>'Estate Agent','frequency'=>162,'icon'=>'shopping_estateagent2',),
 'shop:car' => array('label'=>'Car','frequency'=>159,'icon'=>'shopping_car',),
 'shop:garden_centre' => array('label'=>'Garden Centre','frequency'=>143,'icon'=>'shopping_garden_centre',),
 'shop:car_repair' => array('label'=>'Car Repair','frequency'=>141,'icon'=>'shopping_car_repair',),
 'shop:newsagent' => array('label'=>'Newsagent','frequency'=>132,'icon'=>'',),
 'shop:bakery' => array('label'=>'Bakery','frequency'=>129,'icon'=>'shopping_bakery',),
 'shop:furniture' => array('label'=>'Furniture','frequency'=>124,'icon'=>'',),
 'shop:butcher' => array('label'=>'Butcher','frequency'=>105,'icon'=>'shopping_butcher',),
 'shop:apparel' => array('label'=>'Apparel','frequency'=>98,'icon'=>'shopping_clothes',),
 'shop:electronics' => array('label'=>'Electronics','frequency'=>96,'icon'=>'',),
 'shop:department_store' => array('label'=>'Department Store','frequency'=>86,'icon'=>'',),
 'shop:books' => array('label'=>'Books','frequency'=>85,'icon'=>'',),
 'shop:yes' => array('label'=>'Shop','frequency'=>68,'icon'=>'',),
 'shop:outdoor' => array('label'=>'Outdoor','frequency'=>67,'icon'=>'',),
 'shop:mall' => array('label'=>'Mall','frequency'=>63,'icon'=>'',),
 'shop:florist' => array('label'=>'Florist','frequency'=>61,'icon'=>'',),
 'shop:charity' => array('label'=>'Charity','frequency'=>60,'icon'=>'',),
 'shop:hardware' => array('label'=>'Hardware','frequency'=>59,'icon'=>'',),
 'shop:laundry' => array('label'=>'Laundry','frequency'=>51,'icon'=>'shopping_laundrette',),
 'shop:shoes' => array('label'=>'Shoes','frequency'=>49,'icon'=>'',),
 'shop:beverages' => array('label'=>'Beverages','frequency'=>48,'icon'=>'shopping_alcohol',),
 'shop:dry_cleaning' => array('label'=>'Dry Cleaning','frequency'=>46,'icon'=>'',),
 'shop:carpet' => array('label'=>'Carpet','frequency'=>45,'icon'=>'',),
 'shop:computer' => array('label'=>'Computer','frequency'=>44,'icon'=>'',),
 'shop:alcohol' => array('label'=>'Alcohol','frequency'=>44,'icon'=>'shopping_alcohol',),
 'shop:optician' => array('label'=>'Optician','frequency'=>55,'icon'=>'health_opticians',),
 'shop:chemist' => array('label'=>'Chemist','frequency'=>42,'icon'=>'health_pharmacy',),
 'shop:gallery' => array('label'=>'Gallery','frequency'=>38,'icon'=>'tourist_art_gallery2',),
 'shop:mobile_phone' => array('label'=>'Mobile Phone','frequency'=>37,'icon'=>'',),
 'shop:sports' => array('label'=>'Sports','frequency'=>37,'icon'=>'',),
 'shop:jewelry' => array('label'=>'Jewelry','frequency'=>32,'icon'=>'shopping_jewelry',),
 'shop:pet' => array('label'=>'Pet','frequency'=>29,'icon'=>'',),
 'shop:beauty' => array('label'=>'Beauty','frequency'=>28,'icon'=>'',),
 'shop:stationery' => array('label'=>'Stationery','frequency'=>25,'icon'=>'',),
 'shop:shopping_centre' => array('label'=>'Shopping Centre','frequency'=>25,'icon'=>'',),
 'shop:general' => array('label'=>'General','frequency'=>25,'icon'=>'',),
 'shop:electrical' => array('label'=>'Electrical','frequency'=>25,'icon'=>'',),
 'shop:toys' => array('label'=>'Toys','frequency'=>23,'icon'=>'',),
 'shop:jeweller' => array('label'=>'Jeweller','frequency'=>23,'icon'=>'',),
 'shop:betting' => array('label'=>'Betting','frequency'=>23,'icon'=>'',),
 'shop:household' => array('label'=>'Household','frequency'=>21,'icon'=>'',),
 'shop:travel_agency' => array('label'=>'Travel Agency','frequency'=>21,'icon'=>'',),
 'shop:hifi' => array('label'=>'Hifi','frequency'=>21,'icon'=>'',),
 'amenity:shop' => array('label'=>'Shop','frequency'=>61,'icon'=>'',),
 'tourism:information' => array('label'=>'Information','frequency'=>224,'icon'=>'amenity_information',),

 'place:house' => array('label'=>'House','frequency'=>2086,'icon'=>'','defzoom'=>18,),
 'place:house_name' => array('label'=>'House','frequency'=>2086,'icon'=>'','defzoom'=>18,),
 'place:house_number' => array('label'=>'House Number','frequency'=>2086,'icon'=>'','defzoom'=>18,),
 'place:country_code' => array('label'=>'Country Code','frequency'=>2086,'icon'=>'','defzoom'=>18,),

 //

 'leisure:pitch' => array('label'=>'Pitch','frequency'=>762,'icon'=>'',),
 'highway:unsurfaced' => array('label'=>'Unsurfaced','frequency'=>492,'icon'=>'',),
 'historic:ruins' => array('label'=>'Ruins','frequency'=>483,'icon'=>'tourist_ruin',),
 'amenity:college' => array('label'=>'College','frequency'=>473,'icon'=>'education_school',),
 'historic:monument' => array('label'=>'Monument','frequency'=>470,'icon'=>'tourist_monument',),
 'railway:subway' => array('label'=>'Subway','frequency'=>385,'icon'=>'',),
 'historic:memorial' => array('label'=>'Memorial','frequency'=>382,'icon'=>'tourist_monument',),
 'leisure:nature_reserve' => array('label'=>'Nature Reserve','frequency'=>342,'icon'=>'',),
 'leisure:common' => array('label'=>'Common','frequency'=>322,'icon'=>'',),
 'waterway:lock_gate' => array('label'=>'Lock Gate','frequency'=>321,'icon'=>'',),
 'natural:fell' => array('label'=>'Fell','frequency'=>308,'icon'=>'',),
 'amenity:nightclub' => array('label'=>'Nightclub','frequency'=>292,'icon'=>'',),
 'highway:path' => array('label'=>'Path','frequency'=>287,'icon'=>'',),
 'leisure:garden' => array('label'=>'Garden','frequency'=>285,'icon'=>'',),
 'landuse:reservoir' => array('label'=>'Reservoir','frequency'=>276,'icon'=>'',),
 'leisure:playground' => array('label'=>'Playground','frequency'=>264,'icon'=>'',),
 'leisure:stadium' => array('label'=>'Stadium','frequency'=>212,'icon'=>'',),
 'historic:mine' => array('label'=>'Mine','frequency'=>193,'icon'=>'poi_mine',),
 'natural:cliff' => array('label'=>'Cliff','frequency'=>193,'icon'=>'',),
 'tourism:caravan_site' => array('label'=>'Caravan Site','frequency'=>183,'icon'=>'accommodation_caravan_park',),
 'amenity:bus_station' => array('label'=>'Bus Station','frequency'=>181,'icon'=>'transport_bus_station',),
 'amenity:kindergarten' => array('label'=>'Kindergarten','frequency'=>179,'icon'=>'',),
 'highway:construction' => array('label'=>'Construction','frequency'=>176,'icon'=>'',),
 'amenity:atm' => array('label'=>'Atm','frequency'=>172,'icon'=>'money_atm2',),
 'amenity:emergency_phone' => array('label'=>'Emergency Phone','frequency'=>164,'icon'=>'',),
 'waterway:lock' => array('label'=>'Lock','frequency'=>146,'icon'=>'',),
 'waterway:riverbank' => array('label'=>'Riverbank','frequency'=>143,'icon'=>'',),
 'natural:coastline' => array('label'=>'Coastline','frequency'=>142,'icon'=>'',),
 'tourism:viewpoint' => array('label'=>'Viewpoint','frequency'=>140,'icon'=>'tourist_view_point',),
 'tourism:hostel' => array('label'=>'Hostel','frequency'=>140,'icon'=>'',),
 'tourism:bed_and_breakfast' => array('label'=>'Bed And Breakfast','frequency'=>140,'icon'=>'accommodation_bed_and_breakfast',),
 'railway:halt' => array('label'=>'Halt','frequency'=>135,'icon'=>'',),
 'railway:platform' => array('label'=>'Platform','frequency'=>134,'icon'=>'',),
 'railway:tram' => array('label'=>'Tram','frequency'=>130,'icon'=>'transport_tram_stop',),
 'amenity:courthouse' => array('label'=>'Courthouse','frequency'=>129,'icon'=>'amenity_court',),
 'amenity:recycling' => array('label'=>'Recycling','frequency'=>126,'icon'=>'amenity_recycling',),
 'amenity:dentist' => array('label'=>'Dentist','frequency'=>124,'icon'=>'health_dentist',),
 'natural:beach' => array('label'=>'Beach','frequency'=>121,'icon'=>'tourist_beach',),
 'place:moor' => array('label'=>'Moor','frequency'=>118,'icon'=>'',),
 'amenity:grave_yard' => array('label'=>'Grave Yard','frequency'=>110,'icon'=>'',),
 'waterway:drain' => array('label'=>'Drain','frequency'=>108,'icon'=>'',),
 'landuse:grass' => array('label'=>'Grass','frequency'=>106,'icon'=>'',),
 'landuse:village_green' => array('label'=>'Village Green','frequency'=>106,'icon'=>'',),
 'natural:bay' => array('label'=>'Bay','frequency'=>102,'icon'=>'',),
 'railway:tram_stop' => array('label'=>'Tram Stop','frequency'=>101,'icon'=>'transport_tram_stop',),
 'leisure:marina' => array('label'=>'Marina','frequency'=>98,'icon'=>'',),
 'highway:stile' => array('label'=>'Stile','frequency'=>97,'icon'=>'',),
 'natural:moor' => array('label'=>'Moor','frequency'=>95,'icon'=>'',),
 'railway:light_rail' => array('label'=>'Light Rail','frequency'=>91,'icon'=>'',),
 'railway:narrow_gauge' => array('label'=>'Narrow Gauge','frequency'=>90,'icon'=>'',),
 'natural:land' => array('label'=>'Land','frequency'=>86,'icon'=>'',),
 'amenity:village_hall' => array('label'=>'Village Hall','frequency'=>82,'icon'=>'',),
 'waterway:dock' => array('label'=>'Dock','frequency'=>80,'icon'=>'',),
 'amenity:veterinary' => array('label'=>'Veterinary','frequency'=>79,'icon'=>'',),
 'landuse:brownfield' => array('label'=>'Brownfield','frequency'=>77,'icon'=>'',),
 'leisure:track' => array('label'=>'Track','frequency'=>76,'icon'=>'',),
 'railway:historic_station' => array('label'=>'Historic Station','frequency'=>74,'icon'=>'',),
 'landuse:construction' => array('label'=>'Construction','frequency'=>72,'icon'=>'',),
 'amenity:prison' => array('label'=>'Prison','frequency'=>71,'icon'=>'amenity_prison',),
 'landuse:quarry' => array('label'=>'Quarry','frequency'=>71,'icon'=>'',),
 'amenity:telephone' => array('label'=>'Telephone','frequency'=>70,'icon'=>'',),
 'highway:traffic_signals' => array('label'=>'Traffic Signals','frequency'=>66,'icon'=>'',),
 'natural:heath' => array('label'=>'Heath','frequency'=>62,'icon'=>'',),
 'historic:house' => array('label'=>'House','frequency'=>61,'icon'=>'',),
 'amenity:social_club' => array('label'=>'Social Club','frequency'=>61,'icon'=>'',),
 'landuse:military' => array('label'=>'Military','frequency'=>61,'icon'=>'',),
 'amenity:health_centre' => array('label'=>'Health Centre','frequency'=>59,'icon'=>'',),
 'historic:building' => array('label'=>'Building','frequency'=>58,'icon'=>'',),
 'amenity:clinic' => array('label'=>'Clinic','frequency'=>57,'icon'=>'',),
 'highway:services' => array('label'=>'Services','frequency'=>56,'icon'=>'',),
 'amenity:ferry_terminal' => array('label'=>'Ferry Terminal','frequency'=>55,'icon'=>'',),
 'natural:marsh' => array('label'=>'Marsh','frequency'=>55,'icon'=>'',),
 'natural:hill' => array('label'=>'Hill','frequency'=>54,'icon'=>'',),
 'highway:raceway' => array('label'=>'Raceway','frequency'=>53,'icon'=>'',),
 'amenity:taxi' => array('label'=>'Taxi','frequency'=>47,'icon'=>'',),
 'amenity:take_away' => array('label'=>'Take Away','frequency'=>45,'icon'=>'',),
 'amenity:car_rental' => array('label'=>'Car Rental','frequency'=>44,'icon'=>'',),
 'place:islet' => array('label'=>'Islet','frequency'=>44,'icon'=>'',),
 'amenity:nursery' => array('label'=>'Nursery','frequency'=>44,'icon'=>'',),
 'amenity:nursing_home' => array('label'=>'Nursing Home','frequency'=>43,'icon'=>'',),
 'amenity:toilets' => array('label'=>'Toilets','frequency'=>38,'icon'=>'',),
 'amenity:hall' => array('label'=>'Hall','frequency'=>38,'icon'=>'',),
 'waterway:boatyard' => array('label'=>'Boatyard','frequency'=>36,'icon'=>'',),
 'highway:mini_roundabout' => array('label'=>'Mini Roundabout','frequency'=>35,'icon'=>'',),
 'historic:manor' => array('label'=>'Manor','frequency'=>35,'icon'=>'',),
 'tourism:chalet' => array('label'=>'Chalet','frequency'=>34,'icon'=>'',),
 'amenity:bicycle_parking' => array('label'=>'Bicycle Parking','frequency'=>34,'icon'=>'',),
 'amenity:hotel' => array('label'=>'Hotel','frequency'=>34,'icon'=>'',),
 'waterway:weir' => array('label'=>'Weir','frequency'=>33,'icon'=>'',),
 'natural:wetland' => array('label'=>'Wetland','frequency'=>33,'icon'=>'',),
 'natural:cave_entrance' => array('label'=>'Cave Entrance','frequency'=>32,'icon'=>'',),
 'amenity:crematorium' => array('label'=>'Crematorium','frequency'=>31,'icon'=>'',),
 'tourism:picnic_site' => array('label'=>'Picnic Site','frequency'=>31,'icon'=>'',),
 'landuse:wood' => array('label'=>'Wood','frequency'=>30,'icon'=>'',),
 'landuse:basin' => array('label'=>'Basin','frequency'=>30,'icon'=>'',),
 'natural:tree' => array('label'=>'Tree','frequency'=>30,'icon'=>'',),
 'leisure:slipway' => array('label'=>'Slipway','frequency'=>29,'icon'=>'',),
 'landuse:meadow' => array('label'=>'Meadow','frequency'=>29,'icon'=>'',),
 'landuse:piste' => array('label'=>'Piste','frequency'=>28,'icon'=>'',),
 'amenity:care_home' => array('label'=>'Care Home','frequency'=>28,'icon'=>'',),
 'amenity:club' => array('label'=>'Club','frequency'=>28,'icon'=>'',),
 'amenity:medical_centre' => array('label'=>'Medical Centre','frequency'=>27,'icon'=>'',),
 'historic:roman_road' => array('label'=>'Roman Road','frequency'=>27,'icon'=>'',),
 'historic:fort' => array('label'=>'Fort','frequency'=>26,'icon'=>'',),
 'railway:subway_entrance' => array('label'=>'Subway Entrance','frequency'=>26,'icon'=>'',),
 'historic:yes' => array('label'=>'Historic','frequency'=>25,'icon'=>'',),
 'highway:gate' => array('label'=>'Gate','frequency'=>25,'icon'=>'',),
 'leisure:fishing' => array('label'=>'Fishing','frequency'=>24,'icon'=>'',),
 'historic:museum' => array('label'=>'Museum','frequency'=>24,'icon'=>'',),
 'amenity:car_wash' => array('label'=>'Car Wash','frequency'=>24,'icon'=>'',),
 'railway:level_crossing' => array('label'=>'Level Crossing','frequency'=>23,'icon'=>'',),
 'leisure:bird_hide' => array('label'=>'Bird Hide','frequency'=>23,'icon'=>'',),
 'natural:headland' => array('label'=>'Headland','frequency'=>21,'icon'=>'',),
 'tourism:apartments' => array('label'=>'Apartments','frequency'=>21,'icon'=>'',),
 'amenity:shopping' => array('label'=>'Shopping','frequency'=>21,'icon'=>'',),
 'natural:scrub' => array('label'=>'Scrub','frequency'=>20,'icon'=>'',),
 'natural:fen' => array('label'=>'Fen','frequency'=>20,'icon'=>'',),
 'building:yes' => array('label'=>'Building','frequency'=>200,'icon'=>'',),
 'mountain_pass:yes' => array('label'=>'Mountain Pass','frequency'=>200,'icon'=>'',),

 'amenity:parking' => array('label'=>'Parking','frequency'=>3157,'icon'=>'',),
 'highway:bus_stop' => array('label'=>'Bus Stop','frequency'=>35777,'icon'=>'transport_bus_stop2',),
 'place:postcode' => array('label'=>'Postcode','frequency'=>27267,'icon'=>'',),
 'amenity:post_box' => array('label'=>'Post Box','frequency'=>9613,'icon'=>'',),

 'place:houses' => array('label'=>'Houses','frequency'=>85,'icon'=>'',),
 'railway:preserved' => array('label'=>'Preserved','frequency'=>227,'icon'=>'',),
 'waterway:derelict_canal' => array('label'=>'Derelict Canal','frequency'=>21,'icon'=>'',),
 'amenity:dead_pub' => array('label'=>'Dead Pub','frequency'=>20,'icon'=>'',),
 'railway:disused_station' => array('label'=>'Disused Station','frequency'=>114,'icon'=>'',),
 'railway:abandoned' => array('label'=>'Abandoned','frequency'=>641,'icon'=>'',),
 'railway:disused' => array('label'=>'Disused','frequency'=>72,'icon'=>'',),
				);
	}


	function getClassTypesWithImportance()
	{
		$aOrders = getClassTypes();
		$i = 1;
		foreach($aOrders as $sID => $a)
		{
			$aOrders[$sID]['importance'] = $i++;
		}
		return $aOrders;
	}

	function getResultDiameter($aResult)
	{
		$aClassType = getClassTypes();

		$fDiameter = 0.0001;

		if (isset($aResult['class'])
			  && isset($aResult['type'])
			  && isset($aResult['admin_level'])
			  && isset($aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['defdiameter'])
				&& $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['defdiameter'])
		{
			$fDiameter = $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['defdiameter'];
		}
		elseif (isset($aResult['class'])
			  && isset($aResult['type'])
			  && isset($aClassType[$aResult['class'].':'.$aResult['type']]['defdiameter'])
				&& $aClassType[$aResult['class'].':'.$aResult['type']]['defdiameter'])
		{
			$fDiameter = $aClassType[$aResult['class'].':'.$aResult['type']]['defdiameter'];
		}

		return $fDiameter;
	}


	function javascript_renderData($xVal, $iOptions = 0)
	{
		header("Access-Control-Allow-Origin: *");
		if (defined('PHP_VERSION_ID') && PHP_VERSION_ID > 50400)
			$iOptions |= JSON_UNESCAPED_UNICODE;
		$jsonout = json_encode($xVal, $iOptions);

		if( ! isset($_GET['json_callback']))
		{
			header("Content-Type: application/json; charset=UTF-8");
			echo $jsonout;
		} else
		{
			if (preg_match('/^[$_\p{L}][$_\p{L}\p{Nd}.[\]]*$/u',$_GET['json_callback']))
			{
				header("Content-Type: application/javascript; charset=UTF-8");
				echo $_GET['json_callback'].'('.$jsonout.')';
			}
			else
			{
				header('HTTP/1.0 400 Bad Request');
			}
		}
	}


	function _debugDumpGroupedSearches($aData, $aTokens)
	{
		$aWordsIDs = array();
		if ($aTokens)
		{
			foreach($aTokens as $sToken => $aWords)
			{
				if ($aWords)
				{
					foreach($aWords as $aToken)
					{
						$aWordsIDs[$aToken['word_id']] = $sToken.'('.$aToken['word_id'].')';
					}
				}
			}
		}
		echo "<table border=\"1\">";
		echo "<tr><th>rank</th><th>Name Tokens</th><th>Name Not</th><th>Address Tokens</th><th>Address Not</th><th>country</th><th>operator</th><th>class</th><th>type</th><th>house#</th><th>Lat</th><th>Lon</th><th>Radius</th></tr>";
		foreach($aData as $iRank => $aRankedSet)
		{
			foreach($aRankedSet as $aRow)
			{
				echo "<tr>";
				echo "<td>$iRank</td>";

				echo "<td>";
				$sSep = '';
				foreach($aRow['aName'] as $iWordID)
				{
					echo $sSep.'#'.$aWordsIDs[$iWordID].'#';
					$sSep = ', ';
				}
				echo "</td>";

				echo "<td>";
				$sSep = '';
				foreach($aRow['aNameNonSearch'] as $iWordID)
				{
					echo $sSep.'#'.$aWordsIDs[$iWordID].'#';
					$sSep = ', ';
				}
				echo "</td>";

				echo "<td>";
				$sSep = '';
				foreach($aRow['aAddress'] as $iWordID)
				{
					echo $sSep.'#'.$aWordsIDs[$iWordID].'#';
					$sSep = ', ';
				}
				echo "</td>";

				echo "<td>";
				$sSep = '';
				foreach($aRow['aAddressNonSearch'] as $iWordID)
				{
					echo $sSep.'#'.$aWordsIDs[$iWordID].'#';
					$sSep = ', ';
				}
				echo "</td>";

				echo "<td>".$aRow['sCountryCode']."</td>";

				echo "<td>".$aRow['sOperator']."</td>";
				echo "<td>".$aRow['sClass']."</td>";
				echo "<td>".$aRow['sType']."</td>";

				echo "<td>".$aRow['sHouseNumber']."</td>";

				echo "<td>".$aRow['fLat']."</td>";
				echo "<td>".$aRow['fLon']."</td>";
				echo "<td>".$aRow['fRadius']."</td>";

				echo "</tr>";
			}
		}
		echo "</table>";
	}


	function getAddressDetails(&$oDB, $sLanguagePrefArraySQL, $iPlaceID, $sCountryCode = false, $housenumber = -1, $bRaw = false)
	{
		$sSQL = "select *,get_name_by_language(name,$sLanguagePrefArraySQL) as localname from get_addressdata($iPlaceID, $housenumber)";
		if (!$bRaw) $sSQL .= " WHERE isaddress OR type = 'country_code'";
		$sSQL .= " order by rank_address desc,isaddress desc";

		$aAddressLines = $oDB->getAll($sSQL);
		if (PEAR::IsError($aAddressLines))
		{
			var_dump($aAddressLines);
			exit;
		}
		if ($bRaw) return $aAddressLines;
		//echo "<pre>";
		//var_dump($aAddressLines);
		$aAddress = array();
		$aFallback = array();
		$aClassType = getClassTypes();
		foreach($aAddressLines as $aLine)
		{
			$bFallback = false;
			$aTypeLabel = false;
			if (isset($aClassType[$aLine['class'].':'.$aLine['type'].':'.$aLine['admin_level']])) $aTypeLabel = $aClassType[$aLine['class'].':'.$aLine['type'].':'.$aLine['admin_level']];
			elseif (isset($aClassType[$aLine['class'].':'.$aLine['type']])) $aTypeLabel = $aClassType[$aLine['class'].':'.$aLine['type']];
			elseif (isset($aClassType['boundary:administrative:'.((int)($aLine['rank_address']/2))]))
			{
				$aTypeLabel = $aClassType['boundary:administrative:'.((int)($aLine['rank_address']/2))];
				$bFallback = true;
			}
			else
			{
				$aTypeLabel = array('simplelabel'=>'address'.$aLine['rank_address']);
				$bFallback = true;
			}
			if ($aTypeLabel && ((isset($aLine['localname']) && $aLine['localname']) || (isset($aLine['housenumber']) && $aLine['housenumber'])))
			{
				$sTypeLabel = strtolower(isset($aTypeLabel['simplelabel'])?$aTypeLabel['simplelabel']:$aTypeLabel['label']);
				$sTypeLabel = str_replace(' ','_',$sTypeLabel);
				if (!isset($aAddress[$sTypeLabel]) || (isset($aFallback[$sTypeLabel]) && $aFallback[$sTypeLabel]) || $aLine['class'] == 'place')
				{
					$aAddress[$sTypeLabel] = $aLine['localname']?$aLine['localname']:$aLine['housenumber'];
				}
				$aFallback[$sTypeLabel] = $bFallback;
			}
		}
		return $aAddress;
	}


	function geocodeReverse($fLat, $fLon, $iZoom=18)
	{
		$oDB =& getDB();

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
		$iMaxRank = isset($aZoomRank[$iZoom])?$aZoomRank[$iZoom]:28;

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

			$sSQL = 'select place_id,parent_place_id from placex';
			$sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', geometry, '.$fSearchDiam.')';
			$sSQL .= ' and rank_search != 28 and rank_search >= '.$iMaxRank;
			$sSQL .= ' and (name is not null or housenumber is not null)';
			$sSQL .= ' and class not in (\'waterway\')';
			$sSQL .= ' and (ST_GeometryType(geometry) not in (\'ST_Polygon\',\'ST_MultiPolygon\') ';
			$sSQL .= ' OR ST_DWithin('.$sPointSQL.', ST_Centroid(geometry), '.$fSearchDiam.'))';
			$sSQL .= ' ORDER BY ST_distance('.$sPointSQL.', geometry) ASC limit 1';
			//var_dump($sSQL);
			$aPlace = $oDB->getRow($sSQL);
			if (PEAR::IsError($aPlace))
			{
				var_Dump($sSQL, $aPlace);
				exit;
			}
			$iPlaceID = $aPlace['place_id'];
		}

		// The point we found might be too small - use the address to find what it is a child of
		if ($iPlaceID)
		{
			$sSQL = "select address_place_id from place_addressline where cached_rank_address <= $iMaxRank and place_id = $iPlaceID order by cached_rank_address desc,isaddress desc,distance desc limit 1";
			$iPlaceID = $oDB->getOne($sSQL);
			if (PEAR::IsError($iPlaceID))
			{
				var_Dump($sSQL, $iPlaceID);
				exit;
			}

			if ($iPlaceID && $aPlace['place_id'] && $iMaxRank < 28)
			{
				$sSQL = "select address_place_id from place_addressline where cached_rank_address <= $iMaxRank and place_id = ".$aPlace['place_id']." order by cached_rank_address desc,isaddress desc,distance desc";
				$iPlaceID = $oDB->getOne($sSQL);
				if (PEAR::IsError($iPlaceID))
				{
					var_Dump($sSQL, $iPlaceID);
					exit;
				}
			}
			if (!$iPlaceID)
			{
				$iPlaceID = $aPlace['place_id'];
			}
		}

		return $iPlaceID;
	}

	function addQuotes($s)
	{
		return "'".$s."'";
	}

	// returns boolean
	function validLatLon($fLat,$fLon)
	{
		return ($fLat <= 90.1 && $fLat >= -90.1 && $fLon <= 180.1 && $fLon >= -180.1);
	}

	// Do we have anything that looks like a lat/lon pair?
	// returns array(lat,lon,query_with_lat_lon_removed)
	// or null
	function looksLikeLatLonPair($sQuery)
	{
		$sFound    = null;
		$fQueryLat = null;
		$fQueryLon = null;

		// degrees decimal minutes
		// N 40 26.767, W 79 58.933
		// N 40°26.767′, W 79°58.933′
		//                  1         2                   3                  4         5            6
		if (preg_match('/\\b([NS])[ ]+([0-9]+[0-9.]*)[° ]+([0-9.]+)?[′\']*[, ]+([EW])[ ]+([0-9]+)[° ]+([0-9]+[0-9.]*)[′\']*?\\b/', $sQuery, $aData))
		{
			$sFound    = $aData[0];
			$fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60);
			$fQueryLon = ($aData[4]=='E'?1:-1) * ($aData[5] + $aData[6]/60);
		}
		// degrees decimal minutes
		// 40 26.767 N, 79 58.933 W
		// 40° 26.767′ N 79° 58.933′ W
		//                      1             2                      3          4            5                    6
		elseif (preg_match('/\\b([0-9]+)[° ]+([0-9]+[0-9.]*)?[′\']*[ ]+([NS])[, ]+([0-9]+)[° ]+([0-9]+[0-9.]*)?[′\' ]+([EW])\\b/', $sQuery, $aData))
		{
			$sFound    = $aData[0];
			$fQueryLat = ($aData[3]=='N'?1:-1) * ($aData[1] + $aData[2]/60);
			$fQueryLon = ($aData[6]=='E'?1:-1) * ($aData[4] + $aData[5]/60);
		}
		// degrees decimal seconds
		// N 40 26 46 W 79 58 56
		// N 40° 26′ 46″, W 79° 58′ 56″
		//                      1        2            3            4                5        6            7            8
		elseif (preg_match('/\\b([NS])[ ]([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″"]*[, ]+([EW])[ ]([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″"]*\\b/', $sQuery, $aData))
		{
			$sFound    = $aData[0];
			$fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60 + $aData[4]/3600);
			$fQueryLon = ($aData[5]=='E'?1:-1) * ($aData[6] + $aData[7]/60 + $aData[8]/3600);
		}
		// degrees decimal seconds
		// 40 26 46 N 79 58 56 W
		// 40° 26′ 46″ N, 79° 58′ 56″ W
		//                      1            2            3            4          5            6            7            8
		elseif (preg_match('/\\b([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″" ]+([NS])[, ]+([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″" ]+([EW])\\b/', $sQuery, $aData))
		{
			$sFound    = $aData[0];
			$fQueryLat = ($aData[4]=='N'?1:-1) * ($aData[1] + $aData[2]/60 + $aData[3]/3600);
			$fQueryLon = ($aData[8]=='E'?1:-1) * ($aData[5] + $aData[6]/60 + $aData[7]/3600);
		}
		// degrees decimal
		// N 40.446° W 79.982°
		//                      1        2                               3        4
		elseif (preg_match('/\\b([NS])[ ]([0-9]+[0-9]*\\.[0-9]+)[°]*[, ]+([EW])[ ]([0-9]+[0-9]*\\.[0-9]+)[°]*\\b/', $sQuery, $aData))
		{
			$sFound    = $aData[0];
			$fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2]);
			$fQueryLon = ($aData[3]=='E'?1:-1) * ($aData[4]);
		}
		// degrees decimal
		// 40.446° N 79.982° W
		//                      1                           2          3                           4
		elseif (preg_match('/\\b([0-9]+[0-9]*\\.[0-9]+)[° ]+([NS])[, ]+([0-9]+[0-9]*\\.[0-9]+)[° ]+([EW])\\b/', $sQuery, $aData))
		{
			$sFound    = $aData[0];
			$fQueryLat = ($aData[2]=='N'?1:-1) * ($aData[1]);
			$fQueryLon = ($aData[4]=='E'?1:-1) * ($aData[3]);
		}
		// degrees decimal
		// 12.34, 56.78
		// [12.456,-78.90]
		//                   1          2                             3                        4
		elseif (preg_match('/(\\[|^|\\b)(-?[0-9]+[0-9]*\\.[0-9]+)[, ]+(-?[0-9]+[0-9]*\\.[0-9]+)(\\]|$|\\b)/', $sQuery, $aData))
		{
			$sFound    = $aData[0];
			$fQueryLat = $aData[2];
			$fQueryLon = $aData[3];
		}

		if (!validLatLon($fQueryLat, $fQueryLon)) return;
		$sQuery = trim(str_replace($sFound, ' ', $sQuery));

		return array('lat' => $fQueryLat, 'lon' => $fQueryLon, 'query' => $sQuery);
	}


	function geometryText2Points($geometry_as_text, $fRadius)
	{
		$aPolyPoints = NULL;
		if (preg_match('#POLYGON\\(\\(([- 0-9.,]+)#', $geometry_as_text, $aMatch))
		{
			preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/', $aMatch[1], $aPolyPoints, PREG_SET_ORDER);
		}
		elseif (preg_match('#LINESTRING\\(([- 0-9.,]+)#', $geometry_as_text, $aMatch))
		{
			preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/', $aMatch[1], $aPolyPoints, PREG_SET_ORDER);
		}
		elseif (preg_match('#MULTIPOLYGON\\(\\(\\(([- 0-9.,]+)#', $geometry_as_text, $aMatch))
		{
			preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/', $aMatch[1], $aPolyPoints, PREG_SET_ORDER);
		}
		elseif (preg_match('#POINT\\((-?[0-9.]+) (-?[0-9.]+)\\)#', $geometry_as_text, $aMatch))
		{
			$aPolyPoints = createPointsAroundCenter($aMatch[1], $aMatch[2], $fRadius);
		}

		if (isset($aPolyPoints))
		{
			$aResultPoints = array();
			foreach($aPolyPoints as $aPoint)
			{
				$aResultPoints[] = array($aPoint[1], $aPoint[2]);
			}
			return $aResultPoints;
		}

		return;
	}

	function createPointsAroundCenter($fLon, $fLat, $fRadius)
	{
			$iSteps = max(8, min(100, ($fRadius * 40000)^2));
			$fStepSize = (2*pi())/$iSteps;
			$aPolyPoints = array();
			for($f = 0; $f < 2*pi(); $f += $fStepSize)
			{
				$aPolyPoints[] = array('', $fLon+($fRadius*sin($f)), $fLat+($fRadius*cos($f)) );
			}
			return $aPolyPoints;
	}

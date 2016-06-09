<?php

	function getDetails($aLine){
		$aDetails = array();
		if ($aLine['place_id'])
		{
			$aDetails['place_id'] = $aLine['place_id'];
		}
		$sOSMType = ($aLine['osm_type'] == 'N'?'node':($aLine['osm_type'] == 'W'?'way':($aLine['osm_type'] == 'R'?'relation':($aLine['osm_type'] == 'T'?'tiger':''))));
		if ($sOSMType)
		{
			$aDetails['osm_type'] = $sOSMType;
			$aDetails['osm_id'] = $aLine['osm_id'];
		}
		if ($aLine['localname']) {
			$aDetails['name'] = $aLine['localname'];
		}
		$aDetails['class'] = $aLine['class'];
		$aDetails['type'] = $aLine['type'];
		if ($aLine['housenumber']) {
			$aDetails['housenumber'] = $aLine['housenumber'];
		}
		return $aDetails;
	}

	function wikipedia_link($sWikipedia)
	{
		if ($sWikipedia)
		{
			list($sWikipediaLanguage,$sWikipediaArticle) = explode(':',$sWikipedia);
			return 'https://'.$sWikipediaLanguage.'.wikipedia.org/wiki/'.urlencode($sWikipediaArticle);
		}
		return '';
	}

	header("content-type: application/json; charset=UTF-8");
	$aPlace = array(
		'place_id'=>$aPointDetails['place_id'],
		'licence'=>"Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright"
	);

	$sOSMType = ($aPointDetails['osm_type'] == 'N'?'node':($aPointDetails['osm_type'] == 'W'?'way':($aPointDetails['osm_type'] == 'R'?'relation':($aPointDetails['osm_type'] == 'T'?'tiger':''))));
	if ($sOSMType)
	{
		$aPlace['osm_type'] = $sOSMType;
		$aPlace['osm_id'] = $aPointDetails['osm_id'];
	}

	$aPlace['name'] = $aPointDetails['localname'];
	$aPlace['class'] = $aPointDetails['class'];

	$aPlace['type'] = $aPointDetails['type'];
	$aPlace['lat'] = $aPointDetails['lat'];
	$aPlace['lon'] = $aPointDetails['lon'];
	$aPlace['namedetails'] = $aPointDetails['aNames'];
	if($aPointDetails['wikipedia']) {
		$aPlace['wiki_link'] = wikipedia_link($aPointDetails['wikipedia']);
	} else if ($aPointDetails['aExtraTags']['wikipedia']) {
		$aPlace['wiki_link'] = wikipedia_link($aPointDetails['aExtraTags']['wikipedia']);
	}

	$aPlace['extra_tags'] = $aPointDetails['aExtraTags'];

	if ($aAddressLines) {
		$aAddressDetails = array();
		foreach($aAddressLines as $aAddressLine)
		{
			$aAddressDetails[] = getDetails($aAddressLine);
		}
		$aPlace['address_details'] = $aAddressDetails;
	}

	if ($aLinkedLines) {
		foreach($aLinkedLines as $aLinkedLine)
		{
			$aLinkedPlaces[] = getDetails($aLinkedLine);
		}
		$aPlace['linked_places'] = $aLinkedPlaces;
	}

	if ($aParentOfLines) {
		foreach($aParentOfLines as $aParentOfLine)
		{
			$aChildren[] = getDetails($aParentOfLine);
		}
		$aPlace['children'] = $aChildren;
	}

	javascript_renderData($aPlace);

?>
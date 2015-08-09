<?php
	$aFilteredPlaces = array();

	if (!sizeof($aPlace))
	{
		if (isset($sError))
			$aFilteredPlaces['error'] = $sError;
		else
			$aFilteredPlaces['error'] = 'Unable to geocode';
	}
	else
	{
		if ($aPlace['place_id']) $aFilteredPlaces['place_id'] = $aPlace['place_id'];
		$aFilteredPlaces['licence'] = "Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright";
		$sOSMType = ($aPlace['osm_type'] == 'N'?'node':($aPlace['osm_type'] == 'W'?'way':($aPlace['osm_type'] == 'R'?'relation':'')));
                if ($sOSMType)
                {
                        $aFilteredPlaces['osm_type'] = $sOSMType;
                        $aFilteredPlaces['osm_id'] = $aPlace['osm_id'];
                }
		if (isset($aPlace['lat'])) $aFilteredPlaces['lat'] = $aPlace['lat'];
		if (isset($aPlace['lon'])) $aFilteredPlaces['lon'] = $aPlace['lon'];

		$aFilteredPlaces['place_rank'] = $aPlace['rank_search'];

		$aFilteredPlaces['category'] = $aPlace['class'];
		$aFilteredPlaces['type'] = $aPlace['type'];

		$aFilteredPlaces['importance'] = $aPlace['importance'];

		$aFilteredPlaces['addresstype'] = strtolower($aPlace['addresstype']);

		$aFilteredPlaces['display_name'] = $aPlace['langaddress'];
		$aFilteredPlaces['name'] = $aPlace['placename'];

		if (isset($aPlace['aAddress'])) $aFilteredPlaces['address'] = $aPlace['aAddress'];
		if (isset($aPlace['sExtraTags'])) $aFilteredPlaces['extratags'] = $aPlace['sExtraTags'];
		if (isset($aPlace['sNameDetails'])) $aFilteredPlaces['namedetails'] = $aPlace['sNameDetails'];
	}

	javascript_renderData($aFilteredPlaces, JSON_FORCE_OBJECT);

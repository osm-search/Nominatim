<?php
	$aFilteredPlaces = array();

	if (!sizeof($aPlaces))
	{
		if (isset($sError))
			$aFilteredPlaces['error'] = $sError;
		else
			$aFilteredPlaces['error'] = 'Unable to geocode';
	}
	else
	{
		$aFilteredPlaces['licence'] = "Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright";
		
		foreach ( $aPlaces AS $aPlace )
		{
			$row = array();
			if ($aPlace['place_id']) $row['place_id'] = $aPlace['place_id'];
			$row['name'] = $aPlace['placename'];
			
			$sOSMType = ($aPlace['osm_type'] == 'N'?'node':($aPlace['osm_type'] == 'W'?'way':($aPlace['osm_type'] == 'R'?'relation':'')));
			if ($sOSMType)
			{
				$aFilteredPlaces['osm_type'] = $sOSMType;
				$aFilteredPlaces['osm_id'] = $aPlace['osm_id'];
			}
			if (isset($aPlace['lat'])) $row['lat'] = $aPlace['lat'];
			if (isset($aPlace['lon'])) $row['lon'] = $aPlace['lon'];

			$row['place_rank'] = $aPlace['rank_search'];

			$row['category'] = $aPlace['class'];
			$row['type'] = $aPlace['type'];

			$row['importance'] = $aPlace['importance'];

			$row['addresstype'] = strtolower($aPlace['addresstype']);
			if ($bShowAddressDetails && $aPlace['aAddress'] && sizeof($aPlace['aAddress'])) $row['address'] = $aPlace['aAddress'];
			
			$aFilteredPlaces['results'][] = $row;
		}
	}

	javascript_renderData($aFilteredPlaces);


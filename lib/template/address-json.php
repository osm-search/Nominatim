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
		$aFilteredPlaces['licence'] = CONST_License;
		$sOSMType = ($aPlace['osm_type'] == 'N'?'node':($aPlace['osm_type'] == 'W'?'way':($aPlace['osm_type'] == 'R'?'relation':'')));
                if ($sOSMType)
                {
                        $aFilteredPlaces['osm_type'] = $sOSMType;
                        $aFilteredPlaces['osm_id'] = $aPlace['osm_id'];
                }
                if (isset($aPlace['lat'])) $aFilteredPlaces['lat'] = $aPlace['lat'];
                if (isset($aPlace['lon'])) $aFilteredPlaces['lon'] = $aPlace['lon'];
		$aFilteredPlaces['display_name'] = $aPlace['langaddress'];
		if ($bShowAddressDetails) $aFilteredPlaces['address'] = $aAddress;
	}

	javascript_renderData($aFilteredPlaces);


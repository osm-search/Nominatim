<?php
	header ("Content-Type: application/json; charset=UTF-8");
	header("Access-Control-Allow-Origin: *");

	$aFilteredPlaces = array();

	if (!sizeof($aPlace))
	{
		if ($sError)
			$aFilteredPlaces['error'] = $sError;
		else
			$aFilteredPlaces['error'] = 'Unable to geocode';
	}
	else
	{
		if ($aPlace['place_id']) $aFilteredPlaces['place_id'] = $aPlace['place_id'];
		$aFilteredPlaces['licence'] = "Data Copyright OpenStreetMap Contributors, Some Rights Reserved. CC-BY-SA 2.0.";
		$sOSMType = ($aPlace['osm_type'] == 'N'?'node':($aPlace['osm_type'] == 'W'?'way':($aPlace['osm_type'] == 'R'?'relation':'')));
                if ($sOSMType)
                {
                        $aFilteredPlaces['osm_type'] = $sOSMType;
                        $aFilteredPlaces['osm_id'] = $aPlace['osm_id'];
                }
                $aFilteredPlaces['category'] = $aPlace['class'];
                $aFilteredPlaces['type'] = $aPlace['type'];
                $aFilteredPlaces['addresstype'] = strtolower($aPlace['addresstype']);

		$aFilteredPlaces['display_name'] = $aPlace['langaddress'];
                $aFilteredPlaces['name'] = $aPlace['placename'];
		$aFilteredPlaces['address'] = $aAddress;
	}

	if (isset($_GET['json_callback']) && preg_match('/^[-A-Za-z0-9:_]+$/',$_GET['json_callback']))
	{
		echo $_GET['json_callback'].'('.javascript_renderData($aFilteredPlaces).')';
	}
	else
	{
		echo javascript_renderData($aFilteredPlaces);
	}



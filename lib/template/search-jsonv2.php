<?php
	header("Content-Type: application/json; charset=UTF-8");
	header("Access-Control-Allow-Origin: *");

	$aFilteredPlaces = array();
	foreach($aSearchResults as $iResNum => $aPointDetails)
	{
		$aPlace = array(
				'place_id'=>$aPointDetails['place_id'],
				'licence'=>"Data Copyright OpenStreetMap Contributors, Some Rights Reserved. CC-BY-SA 2.0.",
			);

		$sOSMType = ($aPointDetails['osm_type'] == 'N'?'node':($aPointDetails['osm_type'] == 'W'?'way':($aPointDetails['osm_type'] == 'R'?'relation':'')));
		if ($sOSMType)
		{
			$aPlace['osm_type'] = $sOSMType;
			$aPlace['osm_id'] = $aPointDetails['osm_id'];
		}

                if (isset($aPointDetails['aBoundingBox']))
                {
			$aPlace['boundingbox'] = array(
				$aPointDetails['aBoundingBox'][0],
				$aPointDetails['aBoundingBox'][1],
				$aPointDetails['aBoundingBox'][2],
				$aPointDetails['aBoundingBox'][3]);

			if (isset($aPointDetails['aPolyPoints']) && $bShowPolygons)
			{
				$aPlace['polygonpoints'] = $aPointDetails['aPolyPoints'];
			}
                }

		if (isset($aPointDetails['zoom']))
		{
			$aPlace['zoom'] = $aPointDetails['zoom'];
		}

		$aPlace['lat'] = $aPointDetails['lat'];
		$aPlace['lon'] = $aPointDetails['lon'];
		$aPlace['display_name'] = $aPointDetails['name'];

		$aPlace['category'] = $aPointDetails['class'];
		$aPlace['type'] = $aPointDetails['type'];
		if ($aPointDetails['icon'])
		{
			$aPlace['icon'] = $aPointDetails['icon'];
		}

		if (isset($aPointDetails['address']))
		{
			$aPlace['address'] = $aPointDetails['address'];
                }

		$aFilteredPlaces[] = $aPlace;
	}

	if (isset($_GET['json_callback']) && preg_match('/^[-A-Za-z0-9:_.]+$/',$_GET['json_callback']))
	{
		echo $_GET['json_callback'].'('.javascript_renderData($aFilteredPlaces).')';
	}
	else
	{
		echo javascript_renderData($aFilteredPlaces);
	}

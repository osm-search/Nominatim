<?php
	$aFilteredPlaces = array();
	foreach($aSearchResults as $iResNum => $aPointDetails)
	{
		$aPlace = array(
				'place_id'=>$aPointDetails['place_id'],
				'licence'=>"Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright",
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

		$aPlace['class'] = $aPointDetails['class'];
		$aPlace['type'] = $aPointDetails['type'];
		if (isset($aPointDetails['icon']) && $aPointDetails['icon'])
		{
			$aPlace['icon'] = $aPointDetails['icon'];
		}

		if (isset($aPointDetails['address']))
		{
			$aPlace['address'] = $aPointDetails['address'];
                }

                if (isset($aResult['asgeojson']))
                {
                        $aPlace['geojson'] = json_decode($aResult['asgeojson']);
                }

                if (isset($aResult['assvg']))
                {
                        $aPlace['svg'] = $aResult['assvg'];
                }

                if (isset($aResult['astext']))
                {
                        $aPlace['geotext'] = $aResult['astext'];
                }

		if (isset($aResult['askml']))
		{
			$aPlace['geokml'] = $aResult['askml'];
		}

		$aFilteredPlaces[] = $aPlace;
	}

	javascript_renderData($aFilteredPlaces);

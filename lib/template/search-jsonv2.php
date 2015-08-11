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
		$aPlace['place_rank'] = $aPointDetails['rank_search'];

		$aPlace['category'] = $aPointDetails['class'];
		$aPlace['type'] = $aPointDetails['type'];

		$aPlace['importance'] = $aPointDetails['importance'];

		if (isset($aPointDetails['icon']))
		{
			$aPlace['icon'] = $aPointDetails['icon'];
		}

		if (isset($aPointDetails['address']) && sizeof($aPointDetails['address'])>0)
		{
			$aPlace['address'] = $aPointDetails['address'];
                }

                if (isset($aPointDetails['asgeojson']))
                {
			$aPlace['geojson'] = json_decode($aPointDetails['asgeojson']);
                }

                if (isset($aPointDetails['assvg']))
                {
			$aPlace['svg'] = $aPointDetails['assvg'];
                }

                if (isset($aPointDetails['astext']))
                {
                        $aPlace['geotext'] = $aPointDetails['astext'];
                }

                if (isset($aPointDetails['askml']))
                {
                        $aPlace['geokml'] = $aPointDetails['askml'];
                }

		if (isset($aPointDetails['sExtraTags'])) $aPlace['extratags'] = $aPointDetails['sExtraTags'];
		if (isset($aPointDetails['sNameDetails'])) $aPlace['namedetails'] = $aPointDetails['sNameDetails'];

		$aFilteredPlaces[] = $aPlace;
	}

	javascript_renderData($aFilteredPlaces, array('geojson'));

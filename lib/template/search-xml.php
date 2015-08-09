<?php
	header("content-type: text/xml; charset=UTF-8");

	echo "<";
	echo "?xml version=\"1.0\" encoding=\"UTF-8\" ?";
	echo ">\n";

	echo "<";
	echo (isset($sXmlRootTag)?$sXmlRootTag:'searchresults');
	echo " timestamp='".date(DATE_RFC822)."'";
	echo " attribution='Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright'";
	echo " querystring='".htmlspecialchars($sQuery, ENT_QUOTES)."'";
	if ($sViewBox) echo " viewbox='".htmlspecialchars($sViewBox, ENT_QUOTES)."'";
	echo " polygon='".($bShowPolygons?'true':'false')."'";
	if (sizeof($aExcludePlaceIDs))
	{
		echo " exclude_place_ids='".htmlspecialchars(join(',',$aExcludePlaceIDs))."'";
	}
	if ($sMoreURL)
	{
		echo " more_url='".htmlspecialchars($sMoreURL)."'";
	}
	echo ">\n";

	foreach($aSearchResults as $iResNum => $aResult)
	{
		echo "<place place_id='".$aResult['place_id']."'";
		$sOSMType = ($aResult['osm_type'] == 'N'?'node':($aResult['osm_type'] == 'W'?'way':($aResult['osm_type'] == 'R'?'relation':'')));
		if ($sOSMType)
		{
			echo " osm_type='$sOSMType'";
			echo " osm_id='".$aResult['osm_id']."'";
		}
		echo " place_rank='".$aResult['rank_search']."'";

		if (isset($aResult['aBoundingBox']))
		{
			echo ' boundingbox="';
			echo $aResult['aBoundingBox'][0];
			echo ','.$aResult['aBoundingBox'][1];
			echo ','.$aResult['aBoundingBox'][2];
			echo ','.$aResult['aBoundingBox'][3];
			echo '"';

			if ($bShowPolygons && isset($aResult['aPolyPoints']))
			{
				echo ' polygonpoints=\'';
				echo json_encode($aResult['aPolyPoints']);
				echo '\'';
			}
		}

		if (isset($aResult['asgeojson']))
		{
			echo ' geojson=\'';
			echo $aResult['asgeojson'];
			echo '\'';
		}

		if (isset($aResult['assvg']))
		{
			echo ' geosvg=\'';
			echo $aResult['assvg'];
			echo '\'';
		}

		if (isset($aResult['astext']))
		{
			echo ' geotext=\'';
			echo $aResult['astext'];
			echo '\'';
		}

		if (isset($aResult['zoom']))
		{
			echo " zoom='".$aResult['zoom']."'";
		}

		echo " lat='".$aResult['lat']."'";
		echo " lon='".$aResult['lon']."'";
		echo " display_name='".htmlspecialchars($aResult['name'], ENT_QUOTES)."'";

		echo " class='".htmlspecialchars($aResult['class'])."'";
		echo " type='".htmlspecialchars($aResult['type'], ENT_QUOTES)."'";
		echo " importance='".htmlspecialchars($aResult['importance'])."'";
		if (isset($aResult['icon']) && $aResult['icon'])
		{
			echo " icon='".htmlspecialchars($aResult['icon'], ENT_QUOTES)."'";
		}

		if (isset($aResult['address'])  || isset($aResult['matching']) || isset($aResult['askml']))
		{
			echo ">";
		}

		if (isset($aResult['askml']))
		{
			echo "\n<geokml>";
			echo $aResult['askml'];
			echo "</geokml>";
		}

		if (isset($aResult['address']))
		{
			echo "\n";
			foreach($aResult['address'] as $sKey => $sValue)
			{
				$sKey = str_replace(' ','_',$sKey);
				echo "<$sKey>";
				echo htmlspecialchars($sValue);
				echo "</$sKey>";
			}
		}

		if (isset($aResult['matching']))
		{
			echo "\n<matching>";
			foreach($aResult['matching'] as $sKey => $sValue)
			{
				$sKey = str_replace(' ','_',$sKey);
				$sKey = str_replace(':','-',$sKey);
				echo "<$sKey>";
				echo htmlspecialchars($sValue);
				echo "</$sKey>";
			}
			echo "</matching>";
		}

		if (isset($aResult['address']) || isset($aResult['matching']) || isset($aResult['askml']))
		{
			echo "</place>";
		}
		else
		{
			echo "/>";
		}
	}
	
	echo "</" . (isset($sXmlRootTag)?$sXmlRootTag:'searchresults') . ">";

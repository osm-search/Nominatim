<?php
	header("content-type: text/xml; charset=UTF-8");

	echo "<";
	echo "?xml version=\"1.0\" encoding=\"UTF-8\" ?";
	echo ">\n";

	echo "<places";
	echo " timestamp='".date(DATE_RFC822)."'";
	echo " attribution='Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright'";
	echo ">\n";

	if (!sizeof($aPlaces))
	{
		if (isset($sError))
			echo "<error>$sError</error>";
		else
			echo "<error>Unable to geocode</error>";
	}
	else
	{
		foreach ( $aPlaces AS $aPlace )
		{
			echo "<place";
			if ($aPlace['place_id']) echo ' place_id="'.$aPlace['place_id'].'"';
			$sOSMType = ($aPlace['osm_type'] == 'N'?'node':($aPlace['osm_type'] == 'W'?'way':($aPlace['osm_type'] == 'R'?'relation':'')));
			if ($sOSMType) echo ' osm_type="'.$sOSMType.'"'.' osm_id="'.$aPlace['osm_id'].'"';
			if ($aPlace['ref']) echo ' ref="'.htmlspecialchars($aPlace['ref']).'"';
			if (isset($aPlace['lat'])) echo ' lat="'.htmlspecialchars($aPlace['lat']).'"';
			if (isset($aPlace['lon'])) echo ' lon="'.htmlspecialchars($aPlace['lon']).'"';
			echo ">";
	
			if ($bShowAddressDetails) {
				echo "<addressparts>";
				foreach($aPlace['aAddress'] as $sKey => $sValue)
				{
					$sKey = str_replace(' ','_',$sKey);
					echo "<$sKey>";
					echo htmlspecialchars($sValue);
					echo "</$sKey>";
				}
				echo "</addressparts>";
			}
			echo "</place>";
		}
	}

	echo "</places>";

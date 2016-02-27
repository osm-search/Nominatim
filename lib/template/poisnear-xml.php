<?php
	header("content-type: text/xml; charset=UTF-8");
    echo '<?xml version="1.0" encoding="UTF-8" ?>';
	echo "<poisnear";
	echo " timestamp='".date(DATE_RFC822)."'";
	echo " attribution='Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright'";
	echo " querystring='".htmlspecialchars($_SERVER['QUERY_STRING'], ENT_QUOTES)."'";
	echo ">\n";

	if (!sizeof($aPlaces))
	{
		if (isset($sError))
			echo "<error>$sError</error>";
		else
			echo "<error>Unable to find pois near this point</error>";
	}
	else
	{
        foreach( $aPlaces as $aPlace ){
            echo "<result";
            if ($aPlace['place_id']) echo ' place_id="'.$aPlace['place_id'].'"';
            if (isset($aPlace['osm_id'])) echo ' osm_id="'.$aPlace['osm_id'].'"';
            if (isset($aPlace['distance_km'])) echo ' distance="'.$aPlace['distance_km'].'"';
            if (isset($aPlace['lat'])) echo ' lat="'.htmlspecialchars($aPlace['lat']).'"';
            if (isset($aPlace['lon'])) echo ' lon="'.htmlspecialchars($aPlace['lon']).'"';
            echo ">";
            if (isset($aPlace['name'])){
                 echo '<namedata>';
                 $aName = json_decode( $aPlace['name'] );

                 foreach ($aName as $k=>$v ){
                    $k = str_replace(':','_',$k );
                    echo '<'.$k.'><![CDATA['.$v.']]></'.$k.'>';
                 }
                 echo '</namedata>';
            }
            echo "</result>";
        }
    }

    echo "</poisnear>";

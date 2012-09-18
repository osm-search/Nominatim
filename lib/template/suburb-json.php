<?php

$aFilteredPlaces = array();

foreach ($aParentOfLines as $aAddressLine) {
    $aPlace = array(
        'osm_id' => $aAddressLine['osm_id'],
        'display_name' => trim($aAddressLine['localname']) ? $aAddressLine['localname'] : 'No Name',
        'lat' => $aAddressLine['lat'],
        'lon' => $aAddressLine['lon'],
        'short_name' => $aPointDetails['localname']
    );
    
    $aFilteredPlaces[] = $aPlace;
}


javascript_renderData($aFilteredPlaces);

<?php

$aFilteredPlaces = array();
foreach ($aSearchResults as $iResNum => $aPointDetails) {
    $aPlace = array(
               'type' => 'Feature',
               'properties' => array(
                                'geocoding' => array()
                               )
              );

    if (isset($aPointDetails['place_id'])) $aPlace['properties']['geocoding']['place_id'] = $aPointDetails['place_id'];
    $sOSMType = formatOSMType($aPointDetails['osm_type']);
    if ($sOSMType) {
        $aPlace['properties']['geocoding']['osm_type'] = $sOSMType;
        $aPlace['properties']['geocoding']['osm_id'] = $aPointDetails['osm_id'];
    }

    $aPlace['properties']['geocoding']['type'] = $aPointDetails['type'];

    $aPlace['properties']['geocoding']['label'] = $aPointDetails['langaddress'];

    $aPlace['properties']['geocoding']['name'] = $aPointDetails['placename'];

    if (isset($aPointDetails['address'])) {
        $aPointDetails['address']->addGeocodeJsonAddressParts(
          $aPlace['properties']['geocoding']
        );

        $aPlace['properties']['geocoding']['admin']
            = $aPointDetails['address']->getAdminLevels();
    }

    if (isset($aPointDetails['asgeojson'])) {
        $aPlace['geometry'] = json_decode($aPointDetails['asgeojson']);
    } else {
        $aPlace['geometry'] = array(
                               'type' => 'Point',
                               'coordinates' => array(
                                                 (float) $aPointDetails['lon'],
                                                 (float) $aPointDetails['lat']
                                                )
                              );
    }
    $aFilteredPlaces[] = $aPlace;
}


javascript_renderData(array(
                       'type' => 'FeatureCollection',
                       'geocoding' => array(
                                       'version' => '0.1.0',
                                       'attribution' => 'Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright',
                                       'licence' => 'ODbL',
                                       'query' => $sQuery
                                      ),
                       'features' => $aFilteredPlaces
                      ));

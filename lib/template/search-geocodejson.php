<?php

$aFilteredPlaces = array();
foreach ($aSearchResults as $iResNum => $aPointDetails) {
    $aPlace = array(
               'type' => 'Feature',
               'properties' => array(
                                'geocoding' => array()
                               )
              );

    if (isset($aPlace['place_id'])) $aPlace['properties']['geocoding']['place_id'] = $aPointDetails['place_id'];
    $sOSMType = formatOSMType($aPlace['osm_type']);
    if ($sOSMType) {
        $aPlace['properties']['geocoding']['osm_type'] = $sOSMType;
        $aPlace['properties']['geocoding']['osm_id'] = $aPointDetails['osm_id'];
    }

    $aPlace['properties']['geocoding']['type'] = $aPointDetails['type'];

    $aPlace['properties']['geocoding']['label'] = $aPointDetails['langaddress'];

    $aPlace['properties']['geocoding']['name'] = $aPointDetails['placename'];

    $aFieldMappings = array(
                       'house_number' => 'housenumber',
                       'road' => 'street',
                       'locality' => 'locality',
                       'postcode' => 'postcode',
                       'city' => 'city',
                       'district' => 'district',
                       'county' => 'county',
                       'state' => 'state',
                       'country' => 'country'
                      );

    foreach ($aFieldMappings as $sFrom => $sTo) {
        if (isset($aPointDetails['address'][$sFrom])) {
            $aPlace['properties']['geocoding'][$sTo] = $aPointDetails['address'][$sFrom];
        }
    }

    $aPlace['properties']['geocoding']['admin'] = $aPointDetails['aAddressAdminLevels'];

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

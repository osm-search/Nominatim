<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

$aFilteredPlaces = array();
foreach ($aSearchResults as $iResNum => $aPointDetails) {
    $aPlace = array(
               'type' => 'Feature',
               'properties' => array(
                                'geocoding' => array()
                               )
              );

    if (isset($aPointDetails['place_id'])) {
        $aPlace['properties']['geocoding']['place_id'] = $aPointDetails['place_id'];
    }
    $sOSMType = formatOSMType($aPointDetails['osm_type']);
    if ($sOSMType) {
        $aPlace['properties']['geocoding']['osm_type'] = $sOSMType;
        $aPlace['properties']['geocoding']['osm_id'] = $aPointDetails['osm_id'];
    }
    $aPlace['properties']['geocoding']['osm_key'] = $aPointDetails['class'];
    $aPlace['properties']['geocoding']['osm_value'] = $aPointDetails['type'];

    $aPlace['properties']['geocoding']['type'] = addressRankToGeocodeJsonType($aPointDetails['rank_address']);

    $aPlace['properties']['geocoding']['label'] = $aPointDetails['langaddress'];

    if ($aPointDetails['placename'] !== null) {
        $aPlace['properties']['geocoding']['name'] = $aPointDetails['placename'];
    }

    if (isset($aPointDetails['address'])) {
        $aPointDetails['address']->addGeocodeJsonAddressParts(
            $aPlace['properties']['geocoding']
        );

        $aPlace['properties']['geocoding']['admin']
            = $aPointDetails['address']->getAdminLevels();
    }

    if (isset($aPointDetails['asgeojson'])) {
        $aPlace['geometry'] = json_decode($aPointDetails['asgeojson'], true);
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

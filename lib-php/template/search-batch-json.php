<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

$aOutput = array();
$aOutput['licence'] = 'Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright';
$aOutput['batch'] = array();

foreach ($aBatchResults as $aSearchResults) {
    if (!$aSearchResults) {
        $aSearchResults = array();
    }
    $aFilteredPlaces = array();
    foreach ($aSearchResults as $iResNum => $aPointDetails) {
        $aPlace = array(
                   'place_id'=>$aPointDetails['place_id'],
                  );

        $sOSMType = formatOSMType($aPointDetails['osm_type']);
        if ($sOSMType) {
            $aPlace['osm_type'] = $sOSMType;
            $aPlace['osm_id'] = $aPointDetails['osm_id'];
        }

        if (isset($aPointDetails['aBoundingBox'])) {
            $aPlace['boundingbox'] = array(
                                      $aPointDetails['aBoundingBox'][0],
                                      $aPointDetails['aBoundingBox'][1],
                                      $aPointDetails['aBoundingBox'][2],
                $aPointDetails['aBoundingBox'][3]
                                     );
        }

        if (isset($aPointDetails['zoom'])) {
            $aPlace['zoom'] = $aPointDetails['zoom'];
        }

        $aPlace['lat'] = $aPointDetails['lat'];
        $aPlace['lon'] = $aPointDetails['lon'];
        $aPlace['display_name'] = $aPointDetails['name'];
        $aPlace['place_rank'] = $aPointDetails['rank_search'];

        $aPlace['category'] = $aPointDetails['class'];
        $aPlace['type'] = $aPointDetails['type'];

        $aPlace['importance'] = $aPointDetails['importance'];

        if (isset($aPointDetails['icon'])) {
            $aPlace['icon'] = $aPointDetails['icon'];
        }

        if (isset($aPointDetails['address'])) {
            $aPlace['address'] = $aPointDetails['address']->getAddressNames();
        }

        if (isset($aPointDetails['asgeojson'])) {
            $aPlace['geojson'] = json_decode($aPointDetails['asgeojson'], true);
        }

        if (isset($aPointDetails['assvg'])) {
            $aPlace['svg'] = $aPointDetails['assvg'];
        }

        if (isset($aPointDetails['astext'])) {
            $aPlace['geotext'] = $aPointDetails['astext'];
        }

        if (isset($aPointDetails['askml'])) {
            $aPlace['geokml'] = $aPointDetails['askml'];
        }

        $aFilteredPlaces[] = $aPlace;
    }
    $aOutput['batch'][] = $aFilteredPlaces;
}

javascript_renderData($aOutput, array('geojson'));

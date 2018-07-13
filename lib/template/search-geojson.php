<?php

$aFilteredPlaces = array();
foreach ($aSearchResults as $iResNum => $aPointDetails) {
    $aPlace = array(
               'type' => 'Feature',
               'properties' => array(
                                'place_id'=>$aPointDetails['place_id'],
                               )
              );
    
    $sOSMType = formatOSMType($aPointDetails['osm_type']);
    if ($sOSMType) {
        $aPlace['properties']['osm_type'] = $sOSMType;
        $aPlace['properties']['osm_id'] = $aPointDetails['osm_id'];
    }

    if (isset($aPointDetails['aBoundingBox'])) {
        $aPlace['bbox'] = array(
                           (float) $aPointDetails['aBoundingBox'][2], // minlon
                           (float) $aPointDetails['aBoundingBox'][0], // minlat
                           (float) $aPointDetails['aBoundingBox'][3], // maxlon
                           (float) $aPointDetails['aBoundingBox'][1]  // maxlat
                          );
    }

    if (isset($aPointDetails['zoom'])) {
        $aPlace['properties']['zoom'] = $aPointDetails['zoom'];
    }

    $aPlace['properties']['display_name'] = $aPointDetails['name'];

    $aPlace['properties']['place_rank'] = $aPointDetails['rank_search'];
    $aPlace['properties']['category'] = $aPointDetails['class'];

    $aPlace['properties']['type'] = $aPointDetails['type'];

    $aPlace['properties']['importance'] = $aPointDetails['importance'];

    if (isset($aPointDetails['icon']) && $aPointDetails['icon']) {
        $aPlace['properties']['icon'] = $aPointDetails['icon'];
    }

    if (isset($aPointDetails['address'])) {
        $aPlace['properties']['address'] = $aPointDetails['address']->getAddressNames();
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


    if (isset($aPointDetails['sExtraTags'])) $aPlace['properties']['extratags'] = $aPointDetails['sExtraTags'];
    if (isset($aPointDetails['sNameDetails'])) $aPlace['properties']['namedetails'] = $aPointDetails['sNameDetails'];

    $aFilteredPlaces[] = $aPlace;
}

javascript_renderData(array(
                       'type' => 'FeatureCollection',
                       'licence' => 'Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright',
                       'features' => $aFilteredPlaces
                      ));

<?php

$aFilteredPlaces = array();

if (empty($aPlace)) {
    if (isset($sError)) {
        $aFilteredPlaces['error'] = $sError;
    } else {
        $aFilteredPlaces['error'] = 'Unable to geocode';
    }
    javascript_renderData($aFilteredPlaces);
} else {
    $aFilteredPlaces = array(
                        'type' => 'Feature',
                        'properties' => array()
                       );

    if (isset($aPlace['place_id'])) {
        $aFilteredPlaces['properties']['place_id'] = $aPlace['place_id'];
    }

    $aFilteredPlaces['properties']['licence'] = $aPlace['licence'];

    $aFilteredPlaces['properties']['copyright'] = $aPlace['copyright'];
 
    $sOSMType = formatOSMType($aPlace['osm_type']);
    if ($sOSMType) {
        $aFilteredPlaces['properties']['osm_type'] = $sOSMType;
        $aFilteredPlaces['properties']['osm_id'] = $aPlace['osm_id'];
    }

    $aFilteredPlaces['properties']['place_rank'] = $aPlace['rank_search'];

    $aFilteredPlaces['properties']['category'] = $aPlace['class'];
    $aFilteredPlaces['properties']['type'] = $aPlace['type'];

    $aFilteredPlaces['properties']['importance'] = $aPlace['importance'];

    $aFilteredPlaces['properties']['addresstype'] = strtolower($aPlace['addresstype']);

    $aFilteredPlaces['properties']['name'] = $aPlace['placename'];

    $aFilteredPlaces['properties']['display_name'] = $aPlace['langaddress'];

    if (isset($aPlace['address'])) {
        $aFilteredPlaces['properties']['address'] = $aPlace['address']->getAddressNames();
    }
    if (isset($aPlace['sExtraTags'])) {
        $aFilteredPlaces['properties']['extratags'] = $aPlace['sExtraTags'];
    }
    if (isset($aPlace['sNameDetails'])) {
        $aFilteredPlaces['properties']['namedetails'] = $aPlace['sNameDetails'];
    }

    if (isset($aPlace['aBoundingBox'])) {
        $aFilteredPlaces['bbox'] = array(
                                    (float) $aPlace['aBoundingBox'][2], // minlon
                                    (float) $aPlace['aBoundingBox'][0], // minlat
                                    (float) $aPlace['aBoundingBox'][3], // maxlon
                                    (float) $aPlace['aBoundingBox'][1]  // maxlat
                                   );
    }

    if (isset($aPlace['asgeojson'])) {
        $aFilteredPlaces['geometry'] = json_decode($aPlace['asgeojson']);
    } else {
        $aFilteredPlaces['geometry'] = array(
                                        'type' => 'Point',
                                        'coordinates' => array(
                                                          (float) $aPlace['lon'],
                                                          (float) $aPlace['lat']
                                                         )
                                       );
    }


    javascript_renderData(
        array(
         'type' => 'FeatureCollection',
                        //    'licence' => 'Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright',
         'features' => array($aFilteredPlaces)
        )
    );
}

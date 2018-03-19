<?php

$aPlaceDetails = array();

$aPlaceDetails['place_id'] = (int) $aPointDetails['place_id'];
$aPlaceDetails['parent_place_id'] = (int) $aPointDetails['parent_place_id'];

$aPlaceDetails['osm_type'] = $aPointDetails['osm_type'];
$aPlaceDetails['osm_id'] = (int) $aPointDetails['osm_id'];

$aPlaceDetails['category'] = $aPointDetails['class'];
$aPlaceDetails['type'] = $aPointDetails['type'];
$aPlaceDetails['admin_level'] = $aPointDetails['admin_level'];

$aPlaceDetails['localname'] = $aPointDetails['localname'];
$aPlaceDetails['names'] = $aPointDetails['aNames'];

$aPlaceDetails['addresstags'] = $aPointDetails['aAddressTags'];
$aPlaceDetails['housenumber'] = $aPointDetails['housenumber'];
$aPlaceDetails['postcode'] = $aPointDetails['postcode']; // computed
$aPlaceDetails['country_code'] = $aPointDetails['country_code'];

$aPlaceDetails['indexed_date'] = $aPointDetails['indexed_date'];
$aPlaceDetails['importance'] = (float) $aPointDetails['importance'];
$aPlaceDetails['calculated_importance'] = (float) $aPointDetails['calculated_importance'];

$aPlaceDetails['extratags'] = $aPointDetails['aExtraTags'];
$aPlaceDetails['calculated_wikipedia'] = $aPointDetails['wikipedia'];
$aPlaceDetails['icon'] = $aPointDetails['icon'];

$aPlaceDetails['rank_address'] = (int) $aPointDetails['rank_address'];
$aPlaceDetails['rank_search'] = (int) $aPointDetails['rank_search'];
$aPlaceDetails['rank_search_label'] = $aPointDetails['rank_search_label'];

$aPlaceDetails['isarea'] = ($aPointDetails['isarea'] == 't');
$aPlaceDetails['lat'] = (float) $aPointDetails['lat'];
$aPlaceDetails['lon'] = (float) $aPointDetails['lon'];


$aPlaceDetails['geometry'] = json_decode($aPointDetails['asgeojson']);

$funcMapAddressLines = function ($aFull) {
    $aMapped = [
        'localname' => $aFull['localname'],
        'place_id' => (int) $aFull['place_id'],
        'osm_id' => (int) $aFull['osm_id'],
        'osm_type' => formatOSMType($aFull['osm_type']),
        'class' => $aFull['class'],
        'type' => $aFull['type'],
        'admin_level' => (int) $aFull['admin_level'],
        'rank_address' => (int) $aFull['rank_address'],
        'distance' => (float) $aFull['distance']
    ];
    return $aMapped;
};

$funcMapKeywords = function ($aFull) {
    $aMapped = [
        'id' => (int) $aFull['word_id'],
        'token' => $aFull['word_token']
    ];
    return $aMapped;
};

if ($aAddressLines) {
    $aPlaceDetails['address'] = array_map($funcMapAddressLines, $aAddressLines);
}

if ($aLinkedLines) {
    $aPlaceDetails['linked_places'] = array_map($funcMapAddressLines, $aLinkedLines);
}

if ($bIncludeKeywords) {
    $aPlaceDetails['keywords'] = array();

    if ($aPlaceSearchNameKeywords) {
        $aPlaceDetails['keywords']['name'] = array_map($funcMapKeywords, $aPlaceSearchNameKeywords);
    }

    if ($aPlaceSearchAddressKeywords) {
        $aPlaceDetails['keywords']['address'] = array_map($funcMapKeywords, $aPlaceSearchAddressKeywords);
    }
}

if ($bIncludeChildPlaces) {
    $aPlaceDetails['parentof'] =  array_map($funcMapAddressLines, $aParentOfLines);

    if ($bGroupChildPlaces) {
        $aGroupedAddressLines = [];
        foreach ($aParentOfLines as $aAddressLine) {
            if ($aAddressLine['type'] == 'yes') $sType = $aAddressLine['class'];
            else $sType = $aAddressLine['type'];

            if (!isset($aGroupedAddressLines[$sType]))
                $aGroupedAddressLines[$sType] = [];
            $aGroupedAddressLines[$sType][] = $aAddressLine;
        }
        $aPlaceDetails['parentof'] = $aGroupedAddressLines;
    }
}

javascript_renderData($aPlaceDetails);

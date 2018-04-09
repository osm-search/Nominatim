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
$aPlaceDetails['calculated_postcode'] = $aPointDetails['postcode'];
$aPlaceDetails['country_code'] = $aPointDetails['country_code'];

$aPlaceDetails['indexed_date'] = (new DateTime('@'.$aPointDetails['indexed_epoch']))->format(DateTime::RFC3339);
$aPlaceDetails['importance'] = (float) $aPointDetails['importance'];
$aPlaceDetails['calculated_importance'] = (float) $aPointDetails['calculated_importance'];

$aPlaceDetails['extratags'] = $aPointDetails['aExtraTags'];
$aPlaceDetails['calculated_wikipedia'] = $aPointDetails['wikipedia'];
$aPlaceDetails['icon'] = CONST_Website_BaseURL.'images/mapicons/'.$aPointDetails['icon'].'.n.32.png';

$aPlaceDetails['rank_address'] = (int) $aPointDetails['rank_address'];
$aPlaceDetails['rank_search'] = (int) $aPointDetails['rank_search'];
$aPlaceDetails['rank_search_label'] = $aPointDetails['rank_search_label'];

$aPlaceDetails['isarea'] = ($aPointDetails['isarea'] == 't');
$aPlaceDetails['lat'] = (float) $aPointDetails['lat'];
$aPlaceDetails['lon'] = (float) $aPointDetails['lon'];


$aPlaceDetails['geometry'] = json_decode($aPointDetails['asgeojson']);

$funcMapAddressLine = function ($aFull) {
    $aMapped = array(
        'localname' => $aFull['localname'],
        'place_id' => isset($aFull['place_id']) ? (int) $aFull['place_id'] : null,
        'osm_id' => isset($aFull['osm_id']) ? (int) $aFull['osm_id'] : null,
        'osm_type' => isset($aFull['osm_type']) ? $aFull['osm_type'] : null,
        'class' => $aFull['class'],
        'type' => $aFull['type'],
        'admin_level' => isset($aFull['admin_level']) ? (int) $aFull['admin_level'] : null,
        'rank_address' => $aFull['rank_address'] ? (int) $aFull['rank_address'] : null,
        'distance' => (float) $aFull['distance']
    );

    return $aMapped;
};

$funcMapKeyword = function ($aFull) {
    $aMapped = array(
        'id' => (int) $aFull['word_id'],
        'token' => $aFull['word_token']
    );
    return $aMapped;
};

if ($aAddressLines) {
    $aPlaceDetails['address'] = array_map($funcMapAddressLine, $aAddressLines);
}

if ($aLinkedLines) {
    $aPlaceDetails['linked_places'] = array_map($funcMapAddressLine, $aLinkedLines);
}

if ($bIncludeKeywords) {
    $aPlaceDetails['keywords'] = array();

    if ($aPlaceSearchNameKeywords) {
        $aPlaceDetails['keywords']['name'] = array_map($funcMapKeyword, $aPlaceSearchNameKeywords);
    }

    if ($aPlaceSearchAddressKeywords) {
        $aPlaceDetails['keywords']['address'] = array_map($funcMapKeyword, $aPlaceSearchAddressKeywords);
    }
}

if ($bIncludeHierarchy) {
    if ($bGroupHierarchy) {
        $aPlaceDetails['hierarchy'] = array();
        foreach ($aHierarchyLines as $aAddressLine) {
            if ($aAddressLine['type'] == 'yes') $sType = $aAddressLine['class'];
            else $sType = $aAddressLine['type'];

            if (!isset($aPlaceDetails['hierarchy'][$sType]))
                $aPlaceDetails['hierarchy'][$sType] = array();
            $aPlaceDetails['hierarchy'][$sType][] = $funcMapAddressLine($aAddressLine);
        }
    } else {
        $aPlaceDetails['hierarchy'] = array_map($funcMapAddressLine, $aHierarchyLines);
    }
}

javascript_renderData($aPlaceDetails);

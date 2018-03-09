<?php

$aPlaceDetails = $aPointDetails;

$aPlaceDetails['geojson'] = json_decode($aPointDetails['asgeojson']);
unset($aPlaceDetails['asgeojson']);

if ($aAddressLines) {
    $aPlaceDetails['address_lines'] = $aAddressLines;
}

if ($aLinkedLines) {
    $aPlaceDetails['linked_lines'] = $aLinkedLines;
}

if ($aPlaceSearchNameKeywords) {
    $aPlaceDetails['place_search_name_keywords'] = $aPlaceSearchNameKeywords;
}

if ($aPlaceSearchAddressKeywords) {
    $aPlaceDetails['place_search_address_keywords'] = $aPlaceSearchAddressKeywords;
}

if ($aParentOfLines) {
    $aPlaceDetails['parentof_lines'] = $aParentOfLines;

    if ($bGroupParents) {
        $aGroupedAddressLines = [];
        foreach ($aParentOfLines as $aAddressLine) {
            if ($aAddressLine['type'] == 'yes') $sType = $aAddressLine['class'];
            else $sType = $aAddressLine['type'];

            if (!isset($aGroupedAddressLines[$sType]))
                $aGroupedAddressLines[$sType] = [];
            $aGroupedAddressLines[$sType][] = $aAddressLine;
        }
        $aPlaceDetails['parentof_lines'] = $aGroupedAddressLines;
    }
}

javascript_renderData($aPlaceDetails);

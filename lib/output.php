<?php


function formatOSMType($sType, $bIncludeExternal = true)
{
    if ($sType == 'N') return 'node';
    if ($sType == 'W') return 'way';
    if ($sType == 'R') return 'relation';

    if (!$bIncludeExternal) return '';

    if ($sType == 'T') return 'way';
    if ($sType == 'I') return 'way';

    return '';
}

function osmLink($aFeature, $sRefText = false)
{
    $sOSMType = formatOSMType($aFeature['osm_type'], false);
    if ($sOSMType) {
        return '<a href="//www.openstreetmap.org/'.$sOSMType.'/'.$aFeature['osm_id'].'">'.$sOSMType.' '.($sRefText?$sRefText:$aFeature['osm_id']).'</a>';
    }
    return '';
}

function wikipediaLink($aFeature)
{
    if ($aFeature['wikipedia']) {
        list($sLanguage, $sArticle) = explode(':', $aFeature['wikipedia']);
        return '<a href="https://'.$sLanguage.'.wikipedia.org/wiki/'.urlencode($sArticle).'" target="_blank">'.$aFeature['wikipedia'].'</a>';
    }
    return '';
}

function detailsLink($aFeature, $sTitle = false)
{
    if (!$aFeature['place_id']) return '';

    return '<a href="details.php?place_id='.$aFeature['place_id'].'">'.($sTitle?$sTitle:$aFeature['place_id']).'</a>';
}

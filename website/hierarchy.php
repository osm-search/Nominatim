<?php

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/AddressDetails.php');
require_once(CONST_BasePath.'/lib/output.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();

$sOutputFormat = $oParams->getSet('format', array('html', 'json'), 'html');
$aLangPrefOrder = $oParams->getPreferredLanguages();
$sLanguagePrefArraySQL = 'ARRAY['.join(',', array_map('getDBQuoted', $aLangPrefOrder)).']';

$sPlaceId = $oParams->getString('place_id');
$sOsmType = $oParams->getSet('osmtype', array('N', 'W', 'R'));
$iOsmId = $oParams->getInt('osmid', -1);

$oDB =& getDB();

if ($sOsmType && $iOsmId > 0) {
    $sPlaceId = chksql($oDB->getOne("select place_id from placex where osm_type = '".$sOsmType."' and osm_id = ".$iOsmId." order by type = 'postcode' asc"));

    // Be nice about our error messages for broken geometry
    if (!$sPlaceId) {
        $sSQL = 'select osm_type, osm_id, errormessage, class, type,';
        $sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname,";
        $sSQL .= ' ST_AsText(prevgeometry) as prevgeom, ST_AsText(newgeometry) as newgeom';
        $sSQL .= " from import_polygon_error where osm_type = '".$sOsmType;
        $sSQL .= "' and osm_id = ".$iOsmId.' order by updated desc limit 1';
        $aPointDetails = chksql($oDB->getRow($sSQL));
        if ($aPointDetails) {
            if (preg_match('/\[(-?\d+\.\d+) (-?\d+\.\d+)\]/', $aPointDetails['errormessage'], $aMatches)) {
                $aPointDetails['error_x'] = $aMatches[1];
                $aPointDetails['error_y'] = $aMatches[2];
            }
            include(CONST_BasePath.'/lib/template/details-error-'.$sOutputFormat.'.php');
            exit;
        }
    }
}

if (!$sPlaceId) userError('Please select a place id');

$iPlaceID = (int)$sPlaceId;

if (CONST_Use_US_Tiger_Data) {
    $iParentPlaceID = chksql($oDB->getOne('select parent_place_id from location_property_tiger where place_id = '.$iPlaceID));
    if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
}

if (CONST_Use_Aux_Location_data) {
    $iParentPlaceID = chksql($oDB->getOne('select parent_place_id from location_property_aux where place_id = '.$iPlaceID));
    if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
}


$oAddressLookup = new AddressDetails($oDB, $iPlaceID, -1, $aLangPrefOrder);
$aPlaceAddress = array_reverse($oAddressLookup->getAddressDetails());

if (empty($aPlaceAddress)) userError('Unknown place id.');

$aBreadcrums = array();
foreach ($aPlaceAddress as $i => $aPlace) {
    if (!$aPlace['place_id']) continue;
    $aBreadcrums[] = array(
                      'placeId'   => $aPlace['place_id'],
                      'osmType'   => $aPlace['osm_type'],
                      'osmId'     => $aPlace['osm_id'],
                      'localName' => $aPlace['localname']
                     );

    if ($sOutputFormat == 'html') {
        $sPlaceUrl = 'hierarchy.php?place_id='.$aPlace['place_id'];
        if ($i) echo ' &gt; ';
        echo '<a href="'.$sPlaceUrl.'">'.$aPlace['localname'].'</a> ('.osmLink($aPlace).')';
    }
}


if ($sOutputFormat == 'json') {
    header('content-type: application/json; charset=UTF-8');
    $aDetails = array();
    $aDetails['breadcrumbs'] = $aBreadcrums;
    javascript_renderData($aDetails);
    exit;
}

$aRelatedPlaceIDs = chksql($oDB->getCol($sSQL = "select place_id from placex where linked_place_id = $iPlaceID or place_id = $iPlaceID"));

$sSQL = 'select obj.place_id, osm_type, osm_id, class, type, housenumber, admin_level,';
$sSQL .= " rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea,  st_area(geometry) as area, ";
$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
$sSQL .= ' from (select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, rank_search, geometry, name from placex ';
$sSQL .= ' where parent_place_id in ('.join(',', $aRelatedPlaceIDs).') and name is not null order by rank_address asc,rank_search asc limit 500) as obj';
$sSQL .= ' order by rank_address asc,rank_search asc,localname,class, type,housenumber';
$aParentOfLines = chksql($oDB->getAll($sSQL));

if (!empty($aParentOfLines)) {
    echo '<h2>Parent Of:</h2>';
    $aGroupedAddressLines = array();
    foreach ($aParentOfLines as $aAddressLine) {
        $aAddressLine['label'] = Nominatim\ClassTypes\getProperty($aAddressLine, 'label');
        if (!$aAddressLine['label']) {
            $aAddressLine['label'] = ucwords($aAddressLine['type']);
        }

        if (!isset($aGroupedAddressLines[$aAddressLine['label']])) $aGroupedAddressLines[$aAddressLine['label']] = array();
            $aGroupedAddressLines[$aAddressLine['label']][] = $aAddressLine;
    }

    foreach ($aGroupedAddressLines as $sGroupHeading => $aParentOfLines) {
        echo "<h3>$sGroupHeading</h3>";
        foreach ($aParentOfLines as $aAddressLine) {
            $aAddressLine['localname'] = $aAddressLine['localname']?$aAddressLine['localname']:$aAddressLine['housenumber'];
            $sOSMType = formatOSMType($aAddressLine['osm_type'], false);

            echo '<div class="line">';
            echo '<span class="name">'.(trim($aAddressLine['localname'])?$aAddressLine['localname']:'<span class="noname">No Name</span>').'</span>';
            echo ' (';
            echo '<span class="area">'.($aAddressLine['isarea']=='t'?'Polygon':'Point').'</span>';
            if ($sOSMType) echo ', <span class="osm"><span class="label"></span>'.$sOSMType.' '.osmLink($aAddressLine).'</span>';
            echo ', <a href="hierarchy.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
            echo ', '.$aAddressLine['area'];
            echo ')';
            echo '</div>';
        }
    }
    if (count($aParentOfLines) >= 500) {
        echo '<p>There are more child objects which are not shown.</p>';
    }
    echo '</div>';
}

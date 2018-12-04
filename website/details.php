<?php

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/output.php');
require_once(CONST_BasePath.'/lib/AddressDetails.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();

$sOutputFormat = $oParams->getSet('format', array('html', 'json'), 'html');
set_exception_handler_by_format($sOutputFormat);

$aLangPrefOrder = $oParams->getPreferredLanguages();
$sLanguagePrefArraySQL = 'ARRAY['.join(',', array_map('getDBQuoted', $aLangPrefOrder)).']';

$sPlaceId = $oParams->getString('place_id');
$sOsmType = $oParams->getSet('osmtype', array('N', 'W', 'R'));
$iOsmId = $oParams->getInt('osmid', -1);
$sClass = $oParams->getString('class');

$bIncludeKeywords = $oParams->getBool('keywords', false);
$bIncludeAddressDetails = $oParams->getBool('addressdetails', $sOutputFormat == 'html');
$bIncludeLinkedPlaces = $oParams->getBool('linkedplaces', true);
$bIncludeHierarchy = $oParams->getBool('hierarchy', $sOutputFormat == 'html');
$bGroupHierarchy = $oParams->getBool('group_hierarchy', false);
$bIncludePolygonAsGeoJSON = $oParams->getBool('polygon_geojson', $sOutputFormat == 'html');

$oDB =& getDB();

if ($sOsmType && $iOsmId > 0) {
    $sSQL = sprintf(
        "SELECT place_id FROM placex WHERE osm_type='%s' AND osm_id=%d",
        $sOsmType,
        $iOsmId
    );
    // osm_type and osm_id are not unique enough
    if ($sClass) {
        $sSQL .= " AND class='".$sClass."'";
    }
    $sSQL .= ' ORDER BY class ASC';
    $sPlaceId = chksql($oDB->getOne($sSQL));

    // Be nice about our error messages for broken geometry

    if (!$sPlaceId) {
        $sSQL = 'SELECT ';
        $sSQL .= '    osm_type, ';
        $sSQL .= '    osm_id, ';
        $sSQL .= '    errormessage, ';
        $sSQL .= '    class, ';
        $sSQL .= '    type, ';
        $sSQL .= "    get_name_by_language(name,$sLanguagePrefArraySQL) AS localname,";
        $sSQL .= '    ST_AsText(prevgeometry) AS prevgeom, ';
        $sSQL .= '    ST_AsText(newgeometry) AS newgeom';
        $sSQL .= ' FROM import_polygon_error ';
        $sSQL .= " WHERE osm_type = '".$sOsmType."'";
        $sSQL .= '  AND osm_id = '.$iOsmId;
        $sSQL .= ' ORDER BY updated DESC';
        $sSQL .= ' LIMIT 1';
        $aPointDetails = chksql($oDB->getRow($sSQL));
        if (!PEAR::isError($aPointDetails) && $aPointDetails) {
            if (preg_match('/\[(-?\d+\.\d+) (-?\d+\.\d+)\]/', $aPointDetails['errormessage'], $aMatches)) {
                $aPointDetails['error_x'] = $aMatches[1];
                $aPointDetails['error_y'] = $aMatches[2];
            } else {
                $aPointDetails['error_x'] = 0;
                $aPointDetails['error_y'] = 0;
            }
            include(CONST_BasePath.'/lib/template/details-error-'.$sOutputFormat.'.php');
            exit;
        }
    }
}


if (!$sPlaceId) userError('Please select a place id');

$iPlaceID = (int)$sPlaceId;

if (CONST_Use_US_Tiger_Data) {
    $iParentPlaceID = chksql($oDB->getOne('SELECT parent_place_id FROM location_property_tiger WHERE place_id = '.$iPlaceID));
    if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
}

// interpolated house numbers
$iParentPlaceID = chksql($oDB->getOne('SELECT parent_place_id FROM location_property_osmline WHERE place_id = '.$iPlaceID));
if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;

// artificial postcodes
$iParentPlaceID = chksql($oDB->getOne('SELECT parent_place_id FROM location_postcode WHERE place_id = '.$iPlaceID));
if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;

if (CONST_Use_Aux_Location_data) {
    $iParentPlaceID = chksql($oDB->getOne('SELECT parent_place_id FROM location_property_aux WHERE place_id = '.$iPlaceID));
    if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
}

$hLog = logStart($oDB, 'details', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

// Get the details for this point
$sSQL = 'SELECT place_id, osm_type, osm_id, class, type, name, admin_level,';
$sSQL .= '    housenumber, postcode, country_code,';
$sSQL .= '    importance, wikipedia,';
$sSQL .= '    ROUND(EXTRACT(epoch FROM indexed_date)) AS indexed_epoch,';
$sSQL .= '    parent_place_id, ';
$sSQL .= '    rank_address, ';
$sSQL .= '    rank_search, ';
$sSQL .= '    get_searchrank_label(rank_search) AS rank_search_label,'; // only used in HTML output
$sSQL .= "    get_name_by_language(name,$sLanguagePrefArraySQL) AS localname, ";
$sSQL .= "    ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') AS isarea, ";
$sSQL .= '    ST_y(centroid) AS lat, ';
$sSQL .= '    ST_x(centroid) AS lon, ';
$sSQL .= '    CASE ';
$sSQL .= '       WHEN importance = 0 OR importance IS NULL ';
$sSQL .= '       THEN 0.75-(rank_search::float/40) ';
$sSQL .= '       ELSE importance ';
$sSQL .= '       END as calculated_importance, ';
if ($bIncludePolygonAsGeoJSON) {
    $sSQL .= '    ST_AsGeoJSON(CASE ';
    $sSQL .= '                WHEN ST_NPoints(geometry) > 5000 ';
    $sSQL .= '                THEN ST_SimplifyPreserveTopology(geometry, 0.0001) ';
    $sSQL .= '                ELSE geometry ';
    $sSQL .= '                END) as asgeojson';
} else {
    $sSQL .= '    ST_AsGeoJSON(centroid) as asgeojson';
}
$sSQL .= ' FROM placex ';
$sSQL .= " WHERE place_id = $iPlaceID";

$aPointDetails = chksql($oDB->getRow($sSQL), 'Could not get details of place object.');

if (!$aPointDetails) {
    userError('Unknown place id.');
}

$aPointDetails['localname'] = $aPointDetails['localname']?$aPointDetails['localname']:$aPointDetails['housenumber'];
$aPointDetails['icon'] = Nominatim\ClassTypes\getProperty($aPointDetails, 'icon', false);

// Get all alternative names (languages, etc)
$sSQL = 'SELECT (each(name)).key,(each(name)).value FROM placex ';
$sSQL .= "WHERE place_id = $iPlaceID ORDER BY (each(name)).key";
$aPointDetails['aNames'] = $oDB->getAssoc($sSQL);
if (PEAR::isError($aPointDetails['aNames'])) { // possible timeout
    $aPointDetails['aNames'] = array();
}

// Address tags
$sSQL = 'SELECT (each(address)).key as key,(each(address)).value FROM placex ';
$sSQL .= "WHERE place_id = $iPlaceID ORDER BY key";
$aPointDetails['aAddressTags'] = $oDB->getAssoc($sSQL);
if (PEAR::isError($aPointDetails['aAddressTags'])) { // possible timeout
    $aPointDetails['aAddressTags'] = array();
}

// Extra tags
$sSQL = 'SELECT (each(extratags)).key,(each(extratags)).value FROM placex ';
$sSQL .= "WHERE place_id = $iPlaceID ORDER BY (each(extratags)).key";
$aPointDetails['aExtraTags'] = $oDB->getAssoc($sSQL);
if (PEAR::isError($aPointDetails['aExtraTags'])) { // possible timeout
    $aPointDetails['aExtraTags'] = array();
}

// Address
$aAddressLines = false;
if ($bIncludeAddressDetails) {
    $oDetails = new Nominatim\AddressDetails($oDB, $iPlaceID, -1, $sLanguagePrefArraySQL);
    $aAddressLines = $oDetails->getAddressDetails(true);
}

// Linked places
$aLinkedLines = false;
if ($bIncludeLinkedPlaces) {
    $sSQL = 'SELECT placex.place_id, osm_type, osm_id, class, type, housenumber,';
    $sSQL .= ' admin_level, rank_address, ';
    $sSQL .= " ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') AS isarea,";
    $sSQL .= " ST_DistanceSpheroid(geometry, placegeometry, 'SPHEROID[\"WGS 84\",6378137,298.257223563, AUTHORITY[\"EPSG\",\"7030\"]]') AS distance, ";
    $sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) AS localname, ";
    $sSQL .= ' length(name::text) AS namelength ';
    $sSQL .= ' FROM ';
    $sSQL .= '    placex, ';
    $sSQL .= '    ( ';
    $sSQL .= '      SELECT centroid AS placegeometry ';
    $sSQL .= '      FROM placex ';
    $sSQL .= "      WHERE place_id = $iPlaceID ";
    $sSQL .= '    ) AS x';
    $sSQL .= " WHERE linked_place_id = $iPlaceID";
    $sSQL .= ' ORDER BY ';
    $sSQL .= '   rank_address ASC, ';
    $sSQL .= '   rank_search ASC, ';
    $sSQL .= "   get_name_by_language(name, $sLanguagePrefArraySQL), ";
    $sSQL .= '   housenumber';
    $aLinkedLines = $oDB->getAll($sSQL);
    if (PEAR::isError($aLinkedLines)) { // possible timeout
        $aLinkedLines = array();
    }
}

// All places this is an imediate parent of
$aHierarchyLines = false;
if ($bIncludeHierarchy) {
    $sSQL = 'SELECT obj.place_id, osm_type, osm_id, class, type, housenumber,';
    $sSQL .= " admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') AS isarea,";
    $sSQL .= " ST_DistanceSpheroid(geometry, placegeometry, 'SPHEROID[\"WGS 84\",6378137,298.257223563, AUTHORITY[\"EPSG\",\"7030\"]]') AS distance, ";
    $sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) AS localname, ";
    $sSQL .= ' length(name::text) AS namelength ';
    $sSQL .= ' FROM ';
    $sSQL .= '    ( ';
    $sSQL .= '      SELECT placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, rank_search, geometry, name ';
    $sSQL .= '      FROM placex ';
    $sSQL .= "      WHERE parent_place_id = $iPlaceID ";
    $sSQL .= '      ORDER BY ';
    $sSQL .= '         rank_address ASC, ';
    $sSQL .= '         rank_search ASC ';
    $sSQL .= '      LIMIT 500 ';
    $sSQL .= '    ) AS obj,';
    $sSQL .= '    ( ';
    $sSQL .= '      SELECT centroid AS placegeometry ';
    $sSQL .= '      FROM placex ';
    $sSQL .= "      WHERE place_id = $iPlaceID ";
    $sSQL .= '    ) AS x';
    $sSQL .= ' ORDER BY ';
    $sSQL .= '    rank_address ASC, ';
    $sSQL .= '    rank_search ASC, ';
    $sSQL .= '    localname, ';
    $sSQL .= '    housenumber';
    $aHierarchyLines = $oDB->getAll($sSQL);
    if (PEAR::isError($aHierarchyLines)) { // possible timeout
        $aHierarchyLines = array();
    }
}

$aPlaceSearchNameKeywords = false;
$aPlaceSearchAddressKeywords = false;
if ($bIncludeKeywords) {
    $sSQL = "SELECT * FROM search_name WHERE place_id = $iPlaceID";
    $aPlaceSearchName = $oDB->getRow($sSQL); // can be null
    if (!$aPlaceSearchName || PEAR::isError($aPlaceSearchName)) { // possible timeout
        $aPlaceSearchName = array();
    }

    if (!empty($aPlaceSearchName)) {
        $sSQL = 'SELECT * FROM word WHERE word_id in ('.substr($aPlaceSearchName['name_vector'], 1, -1).')';
        $aPlaceSearchNameKeywords = $oDB->getAll($sSQL);
        if (PEAR::isError($aPlaceSearchNameKeywords)) { // possible timeout
            $aPlaceSearchNameKeywords = array();
        }

        $sSQL = 'SELECT * FROM word WHERE word_id in ('.substr($aPlaceSearchName['nameaddress_vector'], 1, -1).')';
        $aPlaceSearchAddressKeywords = $oDB->getAll($sSQL);
        if (PEAR::isError($aPlaceSearchAddressKeywords)) { // possible timeout
            $aPlaceSearchAddressKeywords = array();
        }
    }
}

logEnd($oDB, $hLog, 1);

if ($sOutputFormat=='html') {
    $sSQL = "SELECT TO_CHAR(lastimportdate,'YYYY/MM/DD HH24:MI')||' GMT' FROM import_status LIMIT 1";
    $sDataDate = chksql($oDB->getOne($sSQL));
    $sTileURL = CONST_Map_Tile_URL;
    $sTileAttribution = CONST_Map_Tile_Attribution;
}

include(CONST_BasePath.'/lib/template/details-'.$sOutputFormat.'.php');

<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

require_once(CONST_LibDir.'/init-website.php');
require_once(CONST_LibDir.'/log.php');
require_once(CONST_LibDir.'/output.php');
require_once(CONST_LibDir.'/AddressDetails.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();

$sOutputFormat = $oParams->getSet('format', array('json'), 'json');
set_exception_handler_by_format($sOutputFormat);

$aLangPrefOrder = $oParams->getPreferredLanguages();

$sPlaceId = $oParams->getString('place_id');
$sOsmType = $oParams->getSet('osmtype', array('N', 'W', 'R'));
$iOsmId = $oParams->getInt('osmid', -1);
$sClass = $oParams->getString('class');

$bIncludeKeywords = $oParams->getBool('keywords', false);
$bIncludeAddressDetails = $oParams->getBool('addressdetails', false);
$bIncludeLinkedPlaces = $oParams->getBool('linkedplaces', true);
$bIncludeHierarchy = $oParams->getBool('hierarchy', false);
$bGroupHierarchy = $oParams->getBool('group_hierarchy', false);
$bIncludePolygonAsGeoJSON = $oParams->getBool('polygon_geojson', false);

$oDB = new Nominatim\DB(CONST_Database_DSN);
$oDB->connect();

$sLanguagePrefArraySQL = $oDB->getArraySQL($oDB->getDBQuotedList($aLangPrefOrder));

if ($sOsmType && $iOsmId > 0) {
    $sSQL = 'SELECT place_id FROM placex WHERE osm_type = :type AND osm_id = :id';
    $aSQLParams = array(':type' => $sOsmType, ':id' => $iOsmId);
    // osm_type and osm_id are not unique enough
    if ($sClass) {
        $sSQL .= ' AND class= :class';
        $aSQLParams[':class'] = $sClass;
    }
    $sSQL .= ' ORDER BY class ASC';
    $sPlaceId = $oDB->getOne($sSQL, $aSQLParams);


    // Nothing? Maybe it's an interpolation.
    // XXX Simply returns the first parent street it finds. It should
    //     get a house number and get the right interpolation.
    if (!$sPlaceId && $sOsmType == 'W' && (!$sClass || $sClass == 'place')) {
        $sSQL = 'SELECT place_id FROM location_property_osmline'
                .' WHERE osm_id = :id LIMIT 1';
        $sPlaceId = $oDB->getOne($sSQL, array(':id' => $iOsmId));
    }

    // Be nice about our error messages for broken geometry

    if (!$sPlaceId && $oDB->tableExists('import_polygon_error')) {
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
        $sSQL .= ' WHERE osm_type = :type';
        $sSQL .= '   AND osm_id = :id';
        $sSQL .= ' ORDER BY updated DESC';
        $sSQL .= ' LIMIT 1';
        $aPointDetails = $oDB->getRow($sSQL, array(':type' => $sOsmType, ':id' => $iOsmId));
        if ($aPointDetails) {
            if (preg_match('/\[(-?\d+\.\d+) (-?\d+\.\d+)\]/', $aPointDetails['errormessage'], $aMatches)) {
                $aPointDetails['error_x'] = $aMatches[1];
                $aPointDetails['error_y'] = $aMatches[2];
            } else {
                $aPointDetails['error_x'] = 0;
                $aPointDetails['error_y'] = 0;
            }
            include(CONST_LibDir.'/template/details-error-'.$sOutputFormat.'.php');
            exit;
        }
    }

    if ($sPlaceId === false) {
        throw new \Exception('No place with that OSM ID found.', 404);
    }
} else {
    if ($sPlaceId === false) {
        userError('Required parameters missing. Need either osmtype/osmid or place_id.');
    }
}

$iPlaceID = (int)$sPlaceId;

if (CONST_Use_US_Tiger_Data) {
    $iParentPlaceID = $oDB->getOne('SELECT parent_place_id FROM location_property_tiger WHERE place_id = '.$iPlaceID);
    if ($iParentPlaceID) {
        $iPlaceID = $iParentPlaceID;
    }
}

// interpolated house numbers
$iParentPlaceID = $oDB->getOne('SELECT parent_place_id FROM location_property_osmline WHERE place_id = '.$iPlaceID);
if ($iParentPlaceID) {
    $iPlaceID = $iParentPlaceID;
}

// artificial postcodes
$iParentPlaceID = $oDB->getOne('SELECT parent_place_id FROM location_postcode WHERE place_id = '.$iPlaceID);
if ($iParentPlaceID) {
    $iPlaceID = $iParentPlaceID;
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

$aPointDetails = $oDB->getRow($sSQL, null, 'Could not get details of place object.');

if (!$aPointDetails) {
    throw new \Exception('No place with that place ID found.', 404);
}

$aPointDetails['localname'] = $aPointDetails['localname']?$aPointDetails['localname']:$aPointDetails['housenumber'];

// Get all alternative names (languages, etc)
$sSQL = 'SELECT (each(name)).key,(each(name)).value FROM placex ';
$sSQL .= "WHERE place_id = $iPlaceID ORDER BY (each(name)).key";
$aPointDetails['aNames'] = $oDB->getAssoc($sSQL);

// Address tags
$sSQL = 'SELECT (each(address)).key as key,(each(address)).value FROM placex ';
$sSQL .= "WHERE place_id = $iPlaceID ORDER BY key";
$aPointDetails['aAddressTags'] = $oDB->getAssoc($sSQL);

// Extra tags
$sSQL = 'SELECT (each(extratags)).key,(each(extratags)).value FROM placex ';
$sSQL .= "WHERE place_id = $iPlaceID ORDER BY (each(extratags)).key";
$aPointDetails['aExtraTags'] = $oDB->getAssoc($sSQL);

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
}

// All places this is an immediate parent of
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
}

$aPlaceSearchNameKeywords = false;
$aPlaceSearchAddressKeywords = false;
if ($bIncludeKeywords) {
    $sSQL = "SELECT * FROM search_name WHERE place_id = $iPlaceID";
    $aPlaceSearchName = $oDB->getRow($sSQL);

    if (!empty($aPlaceSearchName)) {
        $sWordIds = substr($aPlaceSearchName['name_vector'], 1, -1);
        if (!empty($sWordIds)) {
            $sSQL = 'SELECT * FROM word WHERE word_id in ('.$sWordIds.')';
            $aPlaceSearchNameKeywords = $oDB->getAll($sSQL);
        }

        $sWordIds = substr($aPlaceSearchName['nameaddress_vector'], 1, -1);
        if (!empty($sWordIds)) {
            $sSQL = 'SELECT * FROM word WHERE word_id in ('.$sWordIds.')';
            $aPlaceSearchAddressKeywords = $oDB->getAll($sSQL);
        }
    }
}

logEnd($oDB, $hLog, 1);

include(CONST_LibDir.'/template/details-'.$sOutputFormat.'.php');

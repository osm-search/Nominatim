<?php

@define('CONST_ConnectionBucket_PageType', 'Details');

require_once dirname(dirname(__FILE__)).'/settings/settings.php';
require_once CONST_BasePath.'/lib/init-website.php';
require_once CONST_BasePath.'/lib/log.php';
require_once CONST_BasePath.'/lib/output.php';

$sOutputFormat = 'html';

ini_set('memory_limit', '200M');

$oDB =& getDB();

$aLangPrefOrder = getPreferredLanguages();
$sLanguagePrefArraySQL = "ARRAY[".join(',', array_map("getDBQuoted", $aLangPrefOrder))."]";

$sPlaceId = getParamString('place_id');
$sOsmType = getParamSet('osmtype', array('N', 'W', 'R'));
$iOsmId   = getParamInt('osmid', -1);
if ($sOsmType && $iOsmId > 0) {
	$sPlaceId = chksql($oDB->getOne("select place_id from placex where osm_type = '".$sOsmType."' and osm_id = ".$iOsmId." order by type = 'postcode' asc"));

	// Be nice about our error messages for broken geometry
	if (!$sPlaceId) {
		$aPointDetails = chksql($oDB->getRow("select osm_type, osm_id, errormessage, class, type, get_name_by_language(name,$sLanguagePrefArraySQL) as localname, ST_AsText(prevgeometry) as prevgeom, ST_AsText(newgeometry) as newgeom from import_polygon_error where osm_type = '".$sOsmType."' and osm_id = ".$iOsmId." order by updated desc limit 1"));
		if (!PEAR::isError($aPointDetails) && $aPointDetails) {
			if (preg_match('/\[(-?\d+\.\d+) (-?\d+\.\d+)\]/', $aPointDetails['errormessage'], $aMatches)) {
				$aPointDetails['error_x'] = $aMatches[1];
				$aPointDetails['error_y'] = $aMatches[2];
			} else {
				$aPointDetails['error_x'] = 0;
				$aPointDetails['error_y'] = 0;
			}

			include CONST_BasePath.'/lib/template/details-error-'.$sOutputFormat.'.php';
			exit;
		}
	}
}


if (!$sPlaceId) userError("Please select a place id");

$iPlaceID = (int) $sPlaceId;

if (CONST_Use_US_Tiger_Data) {
	$iParentPlaceID = chksql($oDB->getOne('select parent_place_id from location_property_tiger where place_id = '.$iPlaceID));
	if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
}

if (CONST_Use_Aux_Location_data) {
	$iParentPlaceID = chksql($oDB->getOne('select parent_place_id from location_property_aux where place_id = '.$iPlaceID));
	if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
}

$hLog = logStart($oDB, 'details', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

// Get the details for this point
$sSQL  = "select place_id, osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, calculated_country_code as country_code, importance, wikipedia,";
$sSQL .= " to_char(indexed_date, 'YYYY-MM-DD HH24:MI') as indexed_date, parent_place_id, rank_address, rank_search, get_searchrank_label(rank_search) as rank_search_label, get_name_by_language(name,$sLanguagePrefArraySQL) as localname, ";
$sSQL .= " ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, ";
// $sSQL .= " ST_Area(geometry::geography) as area, ";
$sSQL .= " ST_y(centroid) as lat, ST_x(centroid) as lon,";
$sSQL .= " case when importance = 0 OR importance IS NULL then 0.75-(rank_search::float/40) else importance end as calculated_importance, ";
$sSQL .= " ST_AsText(CASE WHEN ST_NPoints(geometry) > 5000 THEN ST_SimplifyPreserveTopology(geometry, 0.0001) ELSE geometry END) as outlinestring";
$sSQL .= " from placex where place_id = $iPlaceID";
$aPointDetails = chksql($oDB->getRow($sSQL), "Could not get details of place object.");
$aPointDetails['localname'] = $aPointDetails['localname'] ? $aPointDetails['localname'] : $aPointDetails['housenumber'];

$aClassType = getClassTypesWithImportance();
$aPointDetails['icon'] = $aClassType[$aPointDetails['class'].':'.$aPointDetails['type']]['icon'];

// Get all alternative names (languages, etc)
$sSQL = "select (each(name)).key,(each(name)).value from placex where place_id = $iPlaceID order by (each(name)).key";
$aPointDetails['aNames'] = $oDB->getAssoc($sSQL);
if (PEAR::isError($aPointDetails['aNames'])) { // possible timeout
	$aPointDetails['aNames'] = [];
}

// Extra tags
$sSQL = "select (each(extratags)).key,(each(extratags)).value from placex where place_id = $iPlaceID order by (each(extratags)).key";
$aPointDetails['aExtraTags'] = $oDB->getAssoc($sSQL);
if (PEAR::isError($aPointDetails['aExtraTags'])) { // possible timeout
	$aPointDetails['aExtraTags'] = [];
}

// Address
$aAddressLines = getAddressDetails($oDB, $sLanguagePrefArraySQL, $iPlaceID, $aPointDetails['country_code'], -1, true);

// Linked places
$sSQL  = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, ST_Distance_Spheroid(geometry, placegeometry, 'SPHEROID[\"WGS 84\",6378137,298.257223563, AUTHORITY[\"EPSG\",\"7030\"]]') as distance, ";
$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
$sSQL .= " from placex, (select centroid as placegeometry from placex where place_id = $iPlaceID) as x";
$sSQL .= " where linked_place_id = $iPlaceID";
$sSQL .= " order by rank_address asc,rank_search asc,get_name_by_language(name,$sLanguagePrefArraySQL),housenumber";
$aLinkedLines = $oDB->getAll($sSQL);
if (PEAR::isError($aLinkedLines)) { // possible timeout
	$aLinkedLines = [];
}

// All places this is an imediate parent of
$sSQL  = "select obj.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, ST_Distance_Spheroid(geometry, placegeometry, 'SPHEROID[\"WGS 84\",6378137,298.257223563, AUTHORITY[\"EPSG\",\"7030\"]]') as distance, ";
$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
$sSQL .= " from (select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, rank_search, geometry, name from placex ";
$sSQL .= " where parent_place_id = $iPlaceID order by rank_address asc,rank_search asc limit 500) as obj,";
$sSQL .= " (select centroid as placegeometry from placex where place_id = $iPlaceID) as x";
$sSQL .= " order by rank_address asc,rank_search asc,localname,housenumber";
$aParentOfLines = $oDB->getAll($sSQL);
if (PEAR::isError($aParentOfLines)) { // possible timeout
	$aParentOfLines = [];
}

$aPlaceSearchNameKeywords = false;
$aPlaceSearchAddressKeywords = false;
if (getParamBool('keywords')) {
	$sSQL = "select * from search_name where place_id = $iPlaceID";
	$aPlaceSearchName = $oDB->getRow($sSQL);
	if (PEAR::isError($aPlaceSearchName)) { // possible timeout
		$aPlaceSearchName = [];
	}

	$sSQL = "select * from word where word_id in (".substr($aPlaceSearchName['name_vector'], 1, -1).")";
	$aPlaceSearchNameKeywords = $oDB->getAll($sSQL);
	if (PEAR::isError($aPlaceSearchNameKeywords)) { // possible timeout
		$aPlaceSearchNameKeywords = [];
	}


	$sSQL = "select * from word where word_id in (".substr($aPlaceSearchName['nameaddress_vector'], 1, -1).")";
	$aPlaceSearchAddressKeywords = $oDB->getAll($sSQL);
	if (PEAR::isError($aPlaceSearchAddressKeywords)) { // possible timeout
		$aPlaceSearchAddressKeywords = [];
	}
}

logEnd($oDB, $hLog, 1);

if ($sOutputFormat == 'html') {
	$sDataDate        = chksql($oDB->getOne("select TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' from import_status limit 1"));
	$sTileURL         = CONST_Map_Tile_URL;
	$sTileAttribution = CONST_Map_Tile_Attribution;
}

require CONST_BasePath.'/lib/template/details-'.$sOutputFormat.'.php';

<?php
require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');

$sOutputFormat = 'json';

// Format for output
if (isset($_GET['format']) && ($_GET['format'] == 'html' || $_GET['format'] == 'json')) {
    $sOutputFormat = $_GET['format'];
}


ini_set('memory_limit', '200M');

$oDB =& getDB();

if (isset($_GET['osmtype']) && isset($_GET['osmid']) && (int) $_GET['osmid'] && ($_GET['osmtype'] == 'N' || $_GET['osmtype'] == 'W' || $_GET['osmtype'] == 'R')) {
    $_GET['place_id'] = $oDB->getOne("select place_id from placex where osm_type = '" . $_GET['osmtype'] . "' and osm_id = " . (int) $_GET['osmid'] . " order by type = 'postcode' asc");
}

if (!isset($_GET['place_id'])) {
    echo "Please select a place id";
    exit;
}

$iPlaceID = (int) $_GET['place_id'];

$iParentPlaceID = $oDB->getOne('select parent_place_id from location_property_tiger where place_id = ' . $iPlaceID);
if ($iParentPlaceID)
    $iPlaceID = $iParentPlaceID;
$iParentPlaceID = $oDB->getOne('select parent_place_id from location_property_aux where place_id = ' . $iPlaceID);
if ($iParentPlaceID)
    $iPlaceID = $iParentPlaceID;

$aLangPrefOrder        = getPreferredLanguages();
$sLanguagePrefArraySQL = "ARRAY[" . join(',', array_map("getDBQuoted", $aLangPrefOrder)) . "]";

$hLog = logStart($oDB, 'details', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

// Make sure the point we are reporting on is fully indexed
//$sSQL = "UPDATE placex set indexed = true where indexed = false and place_id = $iPlaceID";
//$oDB->query($sSQL);


// All places this is an imediate parent of
//
// Searching for suburbs
// First step: search for place:suburb and for boundary:administrative

$sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, st_distance(geometry, placegeometry) as distance, ";
$sSQL .= "ST_X(ST_Centroid(geometry)) as lon, ST_Y(ST_Centroid(geometry)) as lat,";
$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
$sSQL .= " from placex, (select geometry as placegeometry from placex where place_id = $iPlaceID) as x";
$sSQL .= " where parent_place_id = $iPlaceID and ((class = 'place' and type = 'suburb') or (class = 'boundary' and type = 'administrative'))";
$sSQL .= " order by distance";
#$sSQL .= " order by distance,rank_address asc,rank_search asc,get_name_by_language(name,$sLanguagePrefArraySQL),housenumber";

$aParentOfLines = $oDB->getAll($sSQL);

// if there are no search results for place:suburb or boundary:administrative
// Second step: search for place:village

if (!sizeof($aParentOfLines)) {
    $sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, st_distance(geometry, placegeometry) as distance, ";
    $sSQL .= "ST_X(ST_Centroid(geometry)) as lon, ST_Y(ST_Centroid(geometry)) as lat,";
    $sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
    $sSQL .= " from placex, (select geometry as placegeometry from placex where place_id = $iPlaceID) as x";
    $sSQL .= " where parent_place_id = $iPlaceID and (class = 'place' and type = 'village')";
    $sSQL .= " order by distance";
    
    $aParentOfLines = $oDB->getAll($sSQL);
    
}



$aPlaceSearchNameKeywords    = false;
$aPlaceSearchAddressKeywords = false;
if (isset($_GET['keywords']) && $_GET['keywords']) {
    $sSQL                        = "select * from search_name where place_id = $iPlaceID";
    $aPlaceSearchName            = $oDB->getRow($sSQL);
    $sSQL                        = "select * from word where word_id in (" . substr($aPlaceSearchName['name_vector'], 1, -1) . ")";
    $aPlaceSearchNameKeywords    = $oDB->getAll($sSQL);
    $sSQL                        = "select * from word where word_id in (" . substr($aPlaceSearchName['nameaddress_vector'], 1, -1) . ")";
    $aPlaceSearchAddressKeywords = $oDB->getAll($sSQL);
}

logEnd($oDB, $hLog, 1);

include(CONST_BasePath.'/lib/template/suburb-'.$sOutputFormat.'.php');

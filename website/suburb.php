<?php
require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');

$sOutputFormat = 'json';

// Format for output
if (isset($_GET['format']) && ($_GET['format'] == 'html' || $_GET['format'] == 'json')) {
    $sOutputFormat = $_GET['format'];
}

$sSuburbType = '';
$isAddressDetailsQuery = false;

// try to get suburb type (can be suburb or administrative or village)
if (isset($_GET['suburb_type']) && ($_GET['suburb_type'] == 'suburb')) {

    //get suburbs
    $sSuburbType = "(class = 'place' and type = 'suburb')";

} else if (isset($_GET['suburb_type']) && ($_GET['suburb_type'] == 'administrative')) {

    //get administrative
    $sSuburbType = "(class = 'boundary' and type = 'administrative')";

} else if (isset($_GET['suburb_type']) && ($_GET['suburb_type'] == 'village')) {

    //get village
    $sSuburbType = "(class = 'place' and type = 'village')";
} else if (isset($_GET['suburb_type']) && ($_GET['suburb_type'] == 'addresses')) {
    $sSuburbType = "";
    $isAddressDetailsQuery = true;

} else {
    // THIS CAN BE REMOVED, WHEN ALL DEPENDING SYSTEMS GOT AN UPDATE (IMTIS >5.1)
    //get all suburb and administrative
    $sSuburbType = "((class = 'place' and type = 'suburb') or (class = 'boundary' and type = 'administrative'))";
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

$aParentOfLines = array();

if ($isAddressDetailsQuery) {
  $aParentOfLines = getAddressDetails($oDB, $sLanguagePrefArraySQL, $iPlaceID, $aPointDetails['country_code'], true);

} else {

  // Searching for suburbs

  $sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, st_distance(geometry, placegeometry) as distance, ";
  $sSQL .= "ST_X(ST_Centroid(geometry)) as lon, ST_Y(ST_Centroid(geometry)) as lat,";
  $sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
  $sSQL .= " from placex, (select geometry as placegeometry from placex where place_id = $iPlaceID) as x";
  $sSQL .= " where parent_place_id = $iPlaceID and $sSuburbType";
  $sSQL .= " order by distance";


  $aParentOfLines = $oDB->getAll($sSQL);

  // THIS CAN BE REMOVED, WHEN ALL DEPENDING SYSTEMS GOT AN UPDATE (IMTIS >5.1)
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

}


/*
// Get the details for this point
  $sSQL = "select place_id, osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, importance, wikipedia,";
  $sSQL .= " parent_place_id, rank_address, rank_search, get_searchrank_label(rank_search) as rank_search_label, get_name_by_language(name,$sLanguagePrefArraySQL) as localname, ";
  $sSQL .= " ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea,ST_GeometryType(geometry) as geotype, ST_Y(ST_Centroid(geometry)) as lat,ST_X(ST_Centroid(geometry)) as lon ";
  $sSQL .= " from placex where place_id = $iPlaceID";
  $aPointDetails = $oDB->getRow($sSQL);



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

*/

logEnd($oDB, $hLog, 1);

include(CONST_BasePath.'/lib/template/suburb-'.$sOutputFormat.'.php');


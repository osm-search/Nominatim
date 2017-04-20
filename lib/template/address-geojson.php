<?php

$aFilteredPlaces = array();

if (!sizeof($aPlace))
{
    if (isset($sError))
        $aFilteredPlaces['error'] = $sError;
    else
        $aFilteredPlaces['error'] = 'Unable to geocode';
}
else
{
    if ($aPlace['place_id']) $aFilteredPlaces['place_id'] = $aPlace['place_id'];
    $aFilteredPlaces['licence'] = "Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright";
    $sOSMType = formatOSMType($aPlace['osm_type']);
    if ($sOSMType)
    {
        $aFilteredPlaces['osm_type'] = $sOSMType;
        $aFilteredPlaces['osm_id'] = $aPlace['osm_id'];
    }
    if (isset($aPlace['lat'])) $aFilteredPlaces['lat'] = $aPlace['lat'];
    if (isset($aPlace['lon'])) $aFilteredPlaces['lon'] = $aPlace['lon'];

    $aFilteredPlaces['place_rank'] = $aPlace['rank_search'];

    $aFilteredPlaces['category'] = $aPlace['class'];
    $aFilteredPlaces['type'] = $aPlace['type'];

    $aFilteredPlaces['importance'] = $aPlace['importance'];

    $aFilteredPlaces['addresstype'] = strtolower($aPlace['addresstype']);

    $aFilteredPlaces['display_name'] = $aPlace['langaddress'];
    $aFilteredPlaces['name'] = $aPlace['placename'];

    if (isset($aPlace['aAddress'])) $aFilteredPlaces['address'] = $aPlace['aAddress'];
    if (isset($aPlace['sExtraTags'])) $aFilteredPlaces['extratags'] = $aPlace['sExtraTags'];
    if (isset($aPlace['sNameDetails'])) $aFilteredPlaces['namedetails'] = $aPlace['sNameDetails'];

    if (isset($aPlace['aBoundingBox']))
    {
        $aFilteredPlaces['boundingbox'] = $aPlace['aBoundingBox'];
    }

    if (isset($aPlace['geojson']))
    {
        $aFilteredPlaces['geojson'] = json_decode($aPlace['asgeojson']);
    }

    if (isset($aPlace['assvg']))
    {
        $aFilteredPlaces['svg'] = $aPlace['assvg'];
    }

    if (isset($aPlace['astext']))
    {
        $aFilteredPlaces['geotext'] = $aPlace['astext'];
    }

    if (isset($aPlace['askml']))
    {
        $aFilteredPlaces['geokml'] = $aPlace['askml'];
    }

}
/*
"geometry": {
"type": "Point",
"coordinates": [
-58.64107131958008,
-34.59852521332562
]
}
*/
// $aGeoJson = array("type" => "FeatureCollection", "features" => array());
// foreach ($aFilteredPlaces as $aPlace) {
//     $oGeom = isset($aPlace['geojson']) ? $aPlace['geojson'] : false;
//     if ($oGeom) {
//         unset($aPlace['geojson']);
//     } else { // if there is no polygon in response, set the Point geometry
//         $oGeom = array("type"=>"Point","coordinates"=>array($aPlace['lon']*1,$aPlace['lat']*1));
//     }
//     $aGeoJson[] = array(
//         "type" => "Feature", "properties" => $aFilteredPlaces, "geometry" => array("type"=>"Point","coordinates"=>array($aFilteredPlaces['lon']*1,$aFilteredPlaces['lat']*1))
//     );
// }

javascript_renderData(array(
    "type" => "Feature", "properties" => $aFilteredPlaces, "geometry" => array("type"=>"Point","coordinates"=>array($aFilteredPlaces['lon']*1,$aFilteredPlaces['lat']*1))
));

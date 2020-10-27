<?php

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/output.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();
$sOutputFormat = $oParams->getSet('format', array('json'), 'json');
set_exception_handler_by_format($sOutputFormat);

$oDB = new Nominatim\DB();
$oDB->connect();

$sSQL = 'select placex.place_id, country_code,';
$sSQL .= " name->'name' as name, i.* from placex, import_polygon_delete i";
$sSQL .= ' where placex.osm_id = i.osm_id and placex.osm_type = i.osm_type';
$sSQL .= ' and placex.class = i.class and placex.type = i.type';
$aPolygons = $oDB->getAll($sSQL, null, 'Could not get list of deleted OSM elements.');

if (CONST_Debug) {
    var_dump($aPolygons);
    exit;
}

if ($sOutputFormat == 'json') {
    javascript_renderData($aPolygons);
}

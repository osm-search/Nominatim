<?php

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/output.php');
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();
$sOutputFormat = $oParams->getSet('format', array('html', 'json'), 'html');
set_exception_handler_by_format($sOutputFormat);

$iDays = $oParams->getInt('days', false);
$bReduced = $oParams->getBool('reduced', false);
$sClass = $oParams->getString('class', false);

$oDB = new Nominatim\DB();
$oDB->connect();

$iTotalBroken = (int) $oDB->getOne('SELECT count(*) FROM import_polygon_error');

$aPolygons = array();
while ($iTotalBroken && empty($aPolygons)) {
    $sSQL = 'SELECT osm_type, osm_id, class, type, name->\'name\' as "name",';
    $sSQL .= 'country_code, errormessage, updated';
    $sSQL .= ' FROM import_polygon_error';

    $aWhere = array();
    if ($iDays) {
        $aWhere[] = "updated > 'now'::timestamp - '".$iDays." day'::interval";
        $iDays++;
    }

    if ($bReduced) $aWhere[] = "errormessage like 'Area reduced%'";
    if ($sClass) $sWhere[] = "class = '".pg_escape_string($sClass)."'";

    if (!empty($aWhere)) {
        $sSQL .= ' WHERE '.join(' and ', $aWhere);
    }

    $sSQL .= ' ORDER BY updated desc LIMIT 1000';
    $aPolygons = $oDB->getAll($sSQL);
}

if (CONST_Debug) {
    var_dump($aPolygons);
    exit;
}

if ($sOutputFormat == 'json') {
    echo javascript_renderData($aPolygons);
} else {
    include(CONST_BasePath.'/lib/template/polygons-html.php');
}

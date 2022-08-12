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
ini_set('memory_limit', '200M');

$oParams = new Nominatim\ParameterParser();
$sOutputFormat = $oParams->getSet('format', array('json'), 'json');
set_exception_handler_by_format($sOutputFormat);

$iDays = $oParams->getInt('days', false);
$bReduced = $oParams->getBool('reduced', false);
$sClass = $oParams->getString('class', false);

$oDB = new Nominatim\DB(CONST_Database_DSN);
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

    if ($bReduced) {
        $aWhere[] = "errormessage like 'Area reduced%'";
    }
    if ($sClass) {
        $sWhere[] = "class = '".pg_escape_string($sClass)."'";
    }

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
    javascript_renderData($aPolygons);
}

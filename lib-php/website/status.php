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
require_once(CONST_LibDir.'/ParameterParser.php');
require_once(CONST_LibDir.'/Status.php');

$oParams = new Nominatim\ParameterParser();
$sOutputFormat = $oParams->getSet('format', array('text', 'json'), 'text');

$oDB = new Nominatim\DB(CONST_Database_DSN);

if ($sOutputFormat == 'json') {
    header('content-type: application/json; charset=UTF-8');
}


try {
    $oStatus = new Nominatim\Status($oDB);
    $oStatus->status();

    if ($sOutputFormat == 'json') {
        $epoch = $oStatus->dataDate();
        $aResponse = array(
                      'status' => 0,
                      'message' => 'OK',
                      'data_updated' => (new DateTime('@'.$epoch))->format(DateTime::RFC3339),
                      'software_version' => CONST_NominatimVersion
                     );
        $sDatabaseVersion = $oStatus->databaseVersion();
        if ($sDatabaseVersion) {
            $aResponse['database_version'] = $sDatabaseVersion;
        }
        javascript_renderData($aResponse);
    } else {
        echo 'OK';
    }
} catch (Exception $oErr) {
    if ($sOutputFormat == 'json') {
        $aResponse = array(
                      'status' => $oErr->getCode(),
                      'message' => $oErr->getMessage()
                     );
        javascript_renderData($aResponse);
    } else {
        header('HTTP/1.0 500 Internal Server Error');
        echo 'ERROR: '.$oErr->getMessage();
    }
}

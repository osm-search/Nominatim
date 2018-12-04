<?php

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/ParameterParser.php');
require_once(CONST_BasePath.'/lib/Status.php');

$oParams = new Nominatim\ParameterParser();
$sOutputFormat = $oParams->getSet('format', array('text', 'json'), 'text');

$oDB = DB::connect(CONST_Database_DSN, false);
$oStatus = new Nominatim\Status($oDB);


if ($sOutputFormat == 'json') {
    header('content-type: application/json; charset=UTF-8');
}


try {
    $oStatus->status();
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
    exit;
}


if ($sOutputFormat == 'json') {
    $epoch = $oStatus->dataDate();
    $aResponse = array(
                  'status' => 0,
                  'message' => 'OK',
                  'data_updated' => (new DateTime('@'.$epoch))->format(DateTime::RFC3339)
                 );
    javascript_renderData($aResponse);
} else {
    echo 'OK';
}

exit;

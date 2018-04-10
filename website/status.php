<?php

@define('CONST_ConnectionBucket_PageType', 'Status');

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/ParameterParser.php');
require_once(CONST_BasePath.'/lib/Status.php');

$oParams = new Nominatim\ParameterParser();
$sOutputFormat = $oParams->getSet('format', array('text', 'json'), 'text');

$oDB =& DB::connect(CONST_Database_DSN, false);
$oStatus = new Nominatim\Status($oDB);

$aResponse = [
              'status' => 'ok',
              'code' => 200,
              'message' => 'OK'
             ];

$sErrorMsg = $oStatus->status(); // can be nil


if ($sOutputFormat == 'json' && !$sErrorMsg) {
    try {
        $aResponse['data_updated'] = $oStatus->dataDate();
    } catch (Exception $oErr) {
        $sErrorMsg = $oErr->getMessage();
    }
}



if ($sErrorMsg) {
    $aResponse = [
                  'status' => 'error',
                  'code' => 500,
                  'message' => $sErrorMsg
                 ];
}


if ($sErrorMsg) {
    header('HTTP/1.0 500 Internal Server Error');
}

if ($sOutputFormat == 'json') {
    header('content-type: application/json; charset=UTF-8');
    javascript_renderData($aResponse);
} else {
    header('content-type: text/plain; charset=UTF-8');
    if ($sErrorMsg) echo 'ERROR: ';
    echo $aResponse['message'];
}

exit;

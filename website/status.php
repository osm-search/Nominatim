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

$sStatus = $oStatus->status();
$bGotError = ($sStatus != 'OK');

$aResponse = [
              'status' => 'ok',
              'code' => 200,
              'message' => $sStatus
             ];

if (!$bGotError && $sOutputFormat == 'json') {
    try {
        $aResponse['data_updated_date'] = $oStatus->dataDate();
    } catch (Exception $oErr) {
        $bGotError = true;
        $sStatus = $oErr->getMessage();
    }
}



if ($bGotError) {
    $aResponse = [
                  'status' => 'error',
                  'code' => 500,
                  'message' => $sStatus
                 ];
}


if ($bGotError) {
    header('HTTP/1.0 500 Internal Server Error');
}

if ($sOutputFormat == 'json') {
    header('content-type: application/json; charset=UTF-8');
    javascript_renderData($aResponse);
} else {
    header('content-type: text/plain; charset=UTF-8');
    echo ($bGotError ? 'ERROR: '.$sStatus : 'OK');
}

exit;

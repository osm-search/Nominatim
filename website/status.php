<?php

@define('CONST_ConnectionBucket_PageType', 'Status');

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/ParameterParser.php');
require_once(CONST_BasePath.'/lib/Status.php');

$oParams = new Nominatim\ParameterParser();
$sOutputFormat = $oParams->getSet('format', array('text', 'json'), 'text');
$bForceError = $oParams->getBool('force_error', false);

$oDB =& DB::connect(CONST_Database_DSN, false);
$oStatus = new Nominatim\Status($oDB);


$sErrorMsg = $oStatus->status(); // can be nil
if ($bForceError) $sErrorMsg = 'An Error';


if ($sOutputFormat == 'text') {
    if ($sErrorMsg) {
        header('HTTP/1.0 500 Internal Server Error');
        echo 'ERROR: '.$sErrorMsg;
    } else {
        echo 'OK';
    }
    exit;
}

// JSON output

$aResponse = array(
              'status' => 0,
              'message' => 'OK'
             );

if (!$sErrorMsg) {
    try {
        $aResponse['data_updated'] = (new DateTime('@'.$oStatus->dataDate()))->format(DateTime::RFC3339);
    } catch (Exception $oErr) {
        $sErrorMsg = $oErr->getMessage();
    }
}




if ($sErrorMsg) {
    $aResponse = array(
                  'status' => 777,
                  'message' => $sErrorMsg
                 );
// } else {
}

header('content-type: application/json; charset=UTF-8');
javascript_renderData($aResponse);

exit;

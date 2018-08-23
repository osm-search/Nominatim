#!@PHP_BIN@ -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');

$aCMDOptions
 = array(
    'Manage service blocks / restrictions',
    array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
    array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
    array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),
    array('list', 'l', 0, 1, 0, 0, 'bool', 'List recent blocks'),
    array('delete', 'd', 0, 1, 0, 0, 'bool', 'Clear recent blocks list'),
    array('flush', '', 0, 1, 0, 0, 'bool', 'Flush all blocks / stats'),
   );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aResult, true, true);

$m = getBucketMemcache();
if (!$m) {
    echo "ERROR: Bucket memcache is not configured\n";
    exit;
}

if ($aResult['list']) {
    $iCurrentSleeping = $m->get('sleepCounter');
    echo "\n Sleeping blocks count: $iCurrentSleeping\n";

    $aBlocks = getBucketBlocks();
    echo "\n";
    printf(" %-40s | %12s | %7s | %13s | %31s | %8s\n", 'Key', 'Total Blocks', 'Current', 'Still Blocked', 'Last Block Time', 'Sleeping');
    printf(" %'--40s-|-%'-12s-|-%'-7s-|-%'-13s-|-%'-31s-|-%'-8s\n", '', '', '', '', '', '');
    foreach ($aBlocks as $sKey => $aDetails) {
        printf(
            " %-40s | %12s | %7s | %13s | %31s | %8s\n",
            $sKey,
            $aDetails['totalBlocks'],
            (int)$aDetails['currentBucketSize'],
            $aDetails['currentlyBlocked']?'Y':'N',
            date('r', $aDetails['lastBlockTimestamp']),
            $aDetails['isSleeping']?'Y':'N'
        );
    }
    echo "\n";
}

if ($aResult['delete']) {
    $m->set('sleepCounter', 0);
    clearBucketBlocks();
}

if ($aResult['flush']) {
    $m->flush();
}

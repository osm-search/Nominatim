#!/usr/bin/php -Cq
<?php

        require_once(dirname(dirname(__FILE__)).'/lib/init-cmd.php');
        ini_set('memory_limit', '800M');

	$aCMDOptions = array(
		"Manage service blocks / restrictions",
		array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
		array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
		array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),
		array('list', 'l', 0, 1, 0, 0, 'bool', 'List recent blocks'),
		array('delete', 'd', 0, 1, 0, 0, 'bool', 'Clear recent blocks list'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aResult, true, true);

	$m = getBucketMemcache();
        if (!$m)
	{
		echo "ERROR: Bucket memcache is not configured\n";
		exit;
	}

	if ($aResult['list'])
	{
		$aBlocks = getBucketBlocks();
		echo "\n";
		printf(" %-40s | %12s | %7s | %13s | %16s | %31s\n", "Key", "Total Blocks", "Current", "Still Blocked", "Last Req Blocked", "Last Block Time");
		printf(" %'--40s | %'-12s | %'-7s | %'-13s | %'-16s | %'-31s\n", "", "", "", "", "", "");
		foreach($aBlocks as $sKey => $aDetails)
		{
			printf(" %-40s | %12s | %7s | %13s | %16s | %31s\n", $sKey, $aDetails['totalBlocks'], (int)$aDetails['currentBucketSize'], $aDetails['lastRequestBlocked']?'Y':'N', $aDetails['currentlyBlocked']?'Y':'N', date("r", $aDetails['lastBlockTimestamp']));
		}
		echo "\n";
	}

	if ($aResult['delete'])
	{
		clearBucketBlocks();
	}

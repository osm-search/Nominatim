<?php
	require_once('init.php');

	if (CONST_NoAccessControl)
	{
		header("Access-Control-Allow-Origin: *");
		header("Access-Control-Allow-Methods: OPTIONS,GET");
		if (!empty($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']))
		{
			header("Access-Control-Allow-Headers: ".$_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']);
		}
	}
	if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') exit;

	if (CONST_ClosedForIndexing && strpos(CONST_ClosedForIndexingExceptionIPs, ','.$_SERVER["REMOTE_ADDR"].',') === false)
 	{
		echo "Closed for re-indexing...";
		exit;
	}

	$aBucketKeys = array();

	if (isset($_SERVER["HTTP_REFERER"])) $aBucketKeys[] = str_replace('www.','',strtolower(parse_url($_SERVER["HTTP_REFERER"], PHP_URL_HOST)));
	if (isset($_SERVER["REMOTE_ADDR"])) $aBucketKeys[] = $_SERVER["REMOTE_ADDR"];
	if (isset($_GET["email"])) $aBucketKeys[] = $_GET["email"];

	$fBucketVal = doBucket($aBucketKeys, 
			(defined('CONST_ConnectionBucket_PageType')?constant('CONST_ConnectionBucket_Cost_'.CONST_ConnectionBucket_PageType):1) + user_busy_cost(),
			CONST_ConnectionBucket_LeakRate, CONST_ConnectionBucket_BlockLimit);

	if ($fBucketVal > CONST_ConnectionBucket_WaitLimit && $fBucketVal < CONST_ConnectionBucket_BlockLimit)
	{
		$m = getBucketMemcache();
		$iCurrentSleeping = $m->increment('sleepCounter');
		if (false === $iCurrentSleeping)
		{
			$m->add('sleepCounter', 0);
			$iCurrentSleeping = $m->increment('sleepCounter');
		}
		if ($iCurrentSleeping >= CONST_ConnectionBucket_MaxSleeping || isBucketSleeping($aBucketKeys))
		{
			// Too many threads sleeping already.  This becomes a hard block.
			$fBucketVal = doBucket($aBucketKeys, CONST_ConnectionBucket_BlockLimit, CONST_ConnectionBucket_LeakRate, CONST_ConnectionBucket_BlockLimit);
		}
		else
		{
			setBucketSleeping($aBucketKeys, true);
			sleep(($fBucketVal - CONST_ConnectionBucket_WaitLimit)/CONST_ConnectionBucket_LeakRate);
			$fBucketVal = doBucket($aBucketKeys, CONST_ConnectionBucket_LeakRate, CONST_ConnectionBucket_LeakRate, CONST_ConnectionBucket_BlockLimit);
			setBucketSleeping($aBucketKeys, false);
		}
		$m->decrement('sleepCounter');
	}

	if (strpos(CONST_BlockedIPs, ','.$_SERVER["REMOTE_ADDR"].',') !== false || $fBucketVal >= CONST_ConnectionBucket_BlockLimit)
	{
		echo "Your IP has been blocked. \n";
		echo CONST_BlockMessage;
		exit;
	}

	header('Content-type: text/html; charset=utf-8');


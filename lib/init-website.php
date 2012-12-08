<?php
	require_once('init.php');

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

	if (strpos(CONST_BlockedIPs, ','.$_SERVER["REMOTE_ADDR"].',') !== false || $fBucketVal >= CONST_ConnectionBucket_BlockLimit)
	{
		echo "Your IP has been blocked. \n";
		echo "Please create a nominatim trac ticket (http://trac.openstreetmap.org/newticket?component=nominatim) to request this to be removed. \n";
		echo "Information on the Nominatim usage policy can be found here: http://wiki.openstreetmap.org/wiki/Nominatim#Usage_Policy \n";
		exit;
	}

	if ($fBucketVal > CONST_ConnectionBucket_WaitLimit)
	{
		sleep(($fBucketVal - CONST_ConnectionBucket_WaitLimit)/CONST_ConnectionBucket_LeakRate);
	}

	header('Content-type: text/html; charset=utf-8');

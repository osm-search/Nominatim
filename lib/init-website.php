<?php

	require_once('init.php');

	if (CONST_ClosedForIndexing && strpos(CONST_ClosedForIndexingExceptionIPs, ','.$_SERVER["REMOTE_ADDR"].',') === false)
 	{
		echo "Closed for re-indexing...";
		exit;
	}

	if (strpos(CONST_BlockedIPs, ','.$_SERVER["REMOTE_ADDR"].',') !== false)
	{
		echo "Your IP has been blocked. \n";
		echo "Please create a nominatim trac ticket (http://trac.openstreetmap.org/newticket?component=nominatim) to request this to be removed. \n";
		echo "Information on the Nominatim usage policy can be found here: http://wiki.openstreetmap.org/wiki/Nominatim#Usage_Policy \n";
		exit;
	}

	header('Content-type: text/html; charset=utf-8');

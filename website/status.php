<?php
	@define('CONST_ConnectionBucket_PageType', 'Status');

	require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');

	$oDB =& getDB();
	if (!$oDB || PEAR::isError($oDB))
	{
		echo "ERROR: No database";
		exit;
	}

	$iWordID = $oDB->getOne("select word_id,word_token, word, class, type, country_code, operator, search_name_count from word where word_token in (' a')");
	if (PEAR::isError($iWordID))
	{
		echo "ERROR: Query failed";
		exit;
	}
	if (!$iWordID)
	{
		echo "ERROR: No value";
		exit;
	}
	echo "OK";
	exit;


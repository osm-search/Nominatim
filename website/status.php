<?php

@define('CONST_ConnectionBucket_PageType', 'Status');

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-website.php');

function statusError($sMsg)
{
	header("HTTP/1.0 500 Internal Server Error");
	echo "ERROR: ".$sMsg;
	exit;
}

$oDB =& DB::connect(CONST_Database_DSN, false);
if (!$oDB || PEAR::isError($oDB)) {
	statusError("No database");
}

$sStandardWord = $oDB->getOne("select make_standard_name('a')");
if (PEAR::isError($sStandardWord)) {
	statusError("Module failed");
}

if ($sStandardWord != 'a') {
	statusError("Module call failed");
}

$iWordID = $oDB->getOne("select word_id,word_token, word, class, type, country_code, operator, search_name_count from word where word_token in (' a')");
if (PEAR::isError($iWordID)) {
	statusError("Query failed");
}

if (!$iWordID) {
	statusError("No value");
}

echo "OK";
exit;

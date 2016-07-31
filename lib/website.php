<?php

/***************************************************************************
 *
 * Error handling functions
 *
 */
function chksql($oSql, $sMsg = "Database request failed")
{
	if (!PEAR::isError($oSql)) return $oSql;

	header('HTTP/1.0 500 Internal Server Error');
	header('Content-type: text/html; charset=utf-8');

	$sSqlError = $oSql->getMessage();

	echo <<<INTERNALFAIL
<html>
  <head><title>Internal Server Error</title></head>
  <body>
	<h1>Internal Server Error</h1>
	<p>Nominatim has encountered an internal error while accessing the database.
	   This may happen because the database is broken or because of a bug in
	   the software. If you think it is a bug, feel free to report
	   it over on <a href="https://github.com/twain47/Nominatim/issues">
	   Github</a>. Please include the URL that caused the problem and the
	   complete error details below.</p>
	<p><b>Message:</b> $sMsg</p>
	<p><b>SQL Error:</b> $sSqlError</p>
	<p><b>Details:</b> <pre>
INTERNALFAIL;

	if (CONST_Debug) {
		var_dump($oSql);
	} else {
		echo "<pre>\n".$oSql->getUserInfo()."</pre>";
	}

	echo "</pre></p></body></html>";
	exit;
}

function failInternalError($sError, $sSQL = false, $vDumpVar = false)
{
	header('HTTP/1.0 500 Internal Server Error');
	header('Content-type: text/html; charset=utf-8');
	echo "<html><body><h1>Internal Server Error</h1>";
	echo '<p>Nominatim has encountered an internal error while processing your request. This is most likely because of a bug in the software.</p>';
	echo "<p><b>Details:</b> ".$sError,"</p>";
	echo '<p>Feel free to file an issue on <a href="https://github.com/twain47/Nominatim/issues">Github</a>. Please include the error message above and the URL you used.</p>';
	if (CONST_Debug) {
		echo "<hr><h2>Debugging Information</h2><br>";
		if ($sSQL) {
			echo "<h3>SQL query</h3><code>".$sSQL."</code>";
		}
		if ($vDumpVar) {
			echo "<h3>Result</h3> <code>";
			var_dump($vDumpVar);
			echo "</code>";
		}
	}
	echo "\n</body></html>\n";
	exit;
}


function userError($sError)
{
	header('HTTP/1.0 400 Bad Request');
	header('Content-type: text/html; charset=utf-8');
	echo "<html><body><h1>Bad Request</h1>";
	echo '<p>Nominatim has encountered an error with your request.</p>';
	echo "<p><b>Details:</b> ".$sError."</p>";
	echo '<p>If you feel this error is incorrect feel file an issue on <a href="https://github.com/twain47/Nominatim/issues">Github</a>. Please include the error message above and the URL you used.</p>';
	echo "\n</body></html>\n";
	exit;
}


/***************************************************************************
 *
 * Functions for parsing URL parameters
 *
 */

function getParamBool($sName, $bDefault = false)
{
	if (!isset($_GET[$sName]) || strlen($_GET[$sName]) == 0) return $bDefault;

	return (bool) $_GET[$sName];
}

function getParamInt($sName, $bDefault = false)
{
	if (!isset($_GET[$sName]) || strlen($_GET[$sName]) == 0) return $bDefault;

	if (!preg_match('/^[+-]?[0-9]+$/', $_GET[$sName])) {
		userError("Integer number expected for parameter '$sName'");
	}

	return (int) $_GET[$sName];
}

function getParamFloat($sName, $bDefault = false)
{
	if (!isset($_GET[$sName]) || strlen($_GET[$sName]) == 0) return $bDefault;

	if (!preg_match('/^[+-]?[0-9]*\.?[0-9]+$/', $_GET[$sName])) {
		userError("Floating-point number expected for parameter '$sName'");
	}

	return (float) $_GET[$sName];
}

function getParamString($sName, $bDefault = false)
{
	if (!isset($_GET[$sName]) || strlen($_GET[$sName]) == 0) return $bDefault;

	return $_GET[$sName];
}

function getParamSet($sName, $aValues, $sDefault = false)
{
	if (!isset($_GET[$sName]) || strlen($_GET[$sName]) == 0) return $sDefault;

	if (!in_array($_GET[$sName], $aValues)) {
		userError("Parameter '$sName' must be one of: ".join(', ', $aValues));
	}

	return $_GET[$sName];
}

<?php

require_once('init.php');
require_once('ParameterParser.php');

/***************************************************************************
 *
 * Error handling functions
 *
 */


function chksql($oSql, $sMsg = 'Database request failed')
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
       it over on <a href="https://github.com/openstreetmap/Nominatim/issues">
       Github</a>. Please include the URL that caused the problem and the
       complete error details below.</p>
    <p><b>Message:</b> $sMsg</p>
    <p><b>SQL Error:</b> $sSqlError</p>
    <p><b>Details:</b> <pre>
INTERNALFAIL;

    if (CONST_Debug) {
        var_dump($oSql);
    } else {
        echo "<pre>\n".$oSql->getUserInfo().'</pre>';
    }

    echo '</pre></p></body></html>';
    exit;
}

function failInternalError($sError, $sSQL = false, $vDumpVar = false)
{
    header('HTTP/1.0 500 Internal Server Error');
    header('Content-type: text/html; charset=utf-8');
    echo '<html><body><h1>Internal Server Error</h1>';
    echo '<p>Nominatim has encountered an internal error while processing your request. This is most likely because of a bug in the software.</p>';
    echo '<p><b>Details:</b> '.$sError,'</p>';
    echo '<p>Feel free to file an issue on <a href="https://github.com/openstreetmap/Nominatim/issues">Github</a>. ';
    echo 'Please include the error message above and the URL you used.</p>';
    if (CONST_Debug) {
        echo '<hr><h2>Debugging Information</h2><br>';
        if ($sSQL) {
            echo '<h3>SQL query</h3><code>'.$sSQL.'</code>';
        }
        if ($vDumpVar) {
            echo '<h3>Result</h3> <code>';
            var_dump($vDumpVar);
            echo '</code>';
        }
    }
    echo "\n</body></html>\n";
    exit;
}


function userError($sError, $format = "html")
{
    $errortemplate = "/srv/nominatim/lib/template/error-$format.php";
    if(file_exists($errortemplate)){
        require_once $errortemplate;
    }else{
        require_once '/srv/nominatim/lib/template/error-html.php';
    }
}


/***************************************************************************
 * HTTP Reply header setup
 */

if (CONST_NoAccessControl) {
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: OPTIONS,GET');
    if (!empty($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS'])) {
        header('Access-Control-Allow-Headers: '.$_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']);
    }
}
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') exit;

if (CONST_Debug) header('Content-type: text/html; charset=utf-8');

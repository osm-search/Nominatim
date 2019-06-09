<?php

require_once('init.php');
require_once('ParameterParser.php');
require_once(CONST_Debug ? 'DebugHtml.php' : 'DebugNone.php');

/***************************************************************************
 *
 * Error handling functions
 *
 */

function userError($sMsg)
{
    throw new Exception($sMsg, 400);
}


function exception_handler_html($exception)
{
    http_response_code($exception->getCode());
    header('Content-type: text/html; charset=UTF-8');
    include(CONST_BasePath.'/lib/template/error-html.php');
    exit();
}

function exception_handler_json($exception)
{
    http_response_code($exception->getCode());
    header('Content-type: application/json; charset=utf-8');
    include(CONST_BasePath.'/lib/template/error-json.php');
    exit();
}

function exception_handler_xml($exception)
{
    http_response_code($exception->getCode());
    header('Content-type: text/xml; charset=utf-8');
    echo '<?xml version="1.0" encoding="UTF-8" ?>'."\n";
    include(CONST_BasePath.'/lib/template/error-xml.php');
    exit();
}

function shutdown_exception_handler_html()
{
    $error = error_get_last();
    if ($error !== null && $error['type'] === E_ERROR) {
        exception_handler_html(new Exception($error['message'], 500));
    }
}

function shutdown_exception_handler_xml()
{
    $error = error_get_last();
    if ($error !== null && $error['type'] === E_ERROR) {
        exception_handler_xml(new Exception($error['message'], 500));
    }
}

function shutdown_exception_handler_json()
{
    $error = error_get_last();
    if ($error !== null && $error['type'] === E_ERROR) {
        exception_handler_json(new Exception($error['message'], 500));
    }
}


function set_exception_handler_by_format($sFormat = null)
{
    // Multiple calls to register_shutdown_function will cause multiple callbacks
    // to be executed, we only want the last executed. Thus we don't want to register
    // one by default without an explicit $sFormat set.

    if (!isset($sFormat)) {
        set_exception_handler('exception_handler_html');
    } elseif ($sFormat == 'html') {
        set_exception_handler('exception_handler_html');
        register_shutdown_function('shutdown_exception_handler_html');
    } elseif ($sFormat == 'xml') {
        set_exception_handler('exception_handler_xml');
        register_shutdown_function('shutdown_exception_handler_xml');
    } else {
        set_exception_handler('exception_handler_json');
        register_shutdown_function('shutdown_exception_handler_json');
    }
}
// set a default
set_exception_handler_by_format();


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
if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] == 'OPTIONS') exit;

if (CONST_Debug) header('Content-type: text/html; charset=utf-8');

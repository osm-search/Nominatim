<?php

require_once('init.php');
require_once('cmd.php');

// handle http proxy when using file_get_contents
if (CONST_HTTP_Proxy) {
	$proxy = 'tcp://' . CONST_HTTP_Proxy_Host . ':' . CONST_HTTP_Proxy_Port;
	$aHeaders = array();
	if(CONST_HTTP_Proxy_Login != null && CONST_HTTP_Proxy_Login != '' && CONST_HTTP_Proxy_Password != null && CONST_HTTP_Proxy_Password != '') {
		$auth = base64_encode(CONST_HTTP_Proxy_Login . ':' . CONST_HTTP_Proxy_Password);
		$aHeaders = array("Proxy-Authorization: Basic $auth");
	}
	$aContext = array(
		'http' => array(
			'proxy' => $proxy,
			'request_fulluri' => true,
			'header' => $aHeaders
		),
		'https' => array(
			'proxy' => $proxy,
			'request_fulluri' => true,
			'header' => $aHeaders
		)
	);
	stream_context_set_default($aContext);
}

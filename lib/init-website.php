<?php

require_once('init.php');
require_once('website.php');

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

header('Content-type: text/html; charset=utf-8');


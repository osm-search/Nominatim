<?php

	@define('CONST_BasePath', dirname(dirname(__FILE__)));

	// avoid warnings when calling date() function. Can be overwritten
	// in local settings if needed
	date_default_timezone_set('UTC');
  
	require_once(CONST_BasePath.'/settings/settings.php');
	require_once(CONST_BasePath.'/lib/lib.php');
	require_once(CONST_BasePath.'/lib/leakybucket.php');
	require_once(CONST_BasePath.'/lib/db.php');

	if (get_magic_quotes_gpc())
	{
		echo "Please disable magic quotes in your php.ini configuration\n";
		exit;
	}

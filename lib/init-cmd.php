<?php
	if (file_exists(getenv('NOMINATIM_SETTINGS')))
	{
		require_once(getenv('NOMINATIM_SETTINGS'));
	}

	require_once('init.php');
	require_once('cmd.php');

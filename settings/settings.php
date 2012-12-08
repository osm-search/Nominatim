<?php
	if (file_exists(CONST_BasePath.'/settings/local.php')) require_once(CONST_BasePath.'/settings/local.php');
	if (isset($_GET['debug']) && $_GET['debug']) @define('CONST_Debug', true);

	// General settings
	@define('CONST_Debug', false);
	@define('CONST_Database_DSN', 'pgsql://@/nominatim');
	@define('CONST_Max_Word_Frequency', '50000');

	// Paths
	@define('CONST_Postgresql_Version', '9.1');
	@define('CONST_Path_Postgresql_Contrib', '/usr/share/postgresql/'.CONST_Postgresql_Version.'/contrib');
	@define('CONST_Path_Postgresql_Postgis', CONST_Path_Postgresql_Contrib.'/postgis-1.5');
	@define('CONST_Osm2pgsql_Binary', CONST_BasePath.'/osm2pgsql/osm2pgsql');
	@define('CONST_Osmosis_Binary', '/usr/bin/osmosis');

	// Connection buckets to rate limit people being nasty
	@define('CONST_ConnectionBucket_MemcacheServerAddress', false);
	@define('CONST_ConnectionBucket_MemcacheServerPort', 11211);
	@define('CONST_ConnectionBucket_LeakRate', 1);
	@define('CONST_ConnectionBucket_BlockLimit', 10);
	@define('CONST_ConnectionBucket_WaitLimit', 6);
	@define('CONST_ConnectionBucket_MaxSleeping', 10);
	@define('CONST_ConnectionBucket_Cost_Reverse', 1);
	@define('CONST_ConnectionBucket_Cost_Search', 2);
	@define('CONST_ConnectionBucket_Cost_Details', 3);

	// Override this function to add an adjustment factor to the cost
	// based on server load. e.g. getBlockingProcesses
	if (!function_exists('user_busy_cost'))
	{
		function user_busy_cost()
		{
			return 0;
		}
	}

	// Website settings
	@define('CONST_ClosedForIndexing', false);
	@define('CONST_ClosedForIndexingExceptionIPs', '');
	@define('CONST_BlockedIPs', '');
	@define('CONST_BulkUserIPs', '');

	@define('CONST_Website_BaseURL', 'http://'.php_uname('n').'/');
	@define('CONST_Tile_Default', 'Mapnik');

	@define('CONST_Default_Language', 'xx');
	@define('CONST_Default_Lat', 20.0);
	@define('CONST_Default_Lon', 0.0);
	@define('CONST_Default_Zoom', 2);

	@define('CONST_Search_AreaPolygons_Enabled', true);
	@define('CONST_Search_AreaPolygons', true);

	@define('CONST_Suggestions_Enabled', false);

	@define('CONST_Search_TryDroppedAddressTerms', false);

	// Set to zero to disable polygon output
	@define('CONST_PolygonOutput_MaximumTypes', 1);

	// Log settings
	@define('CONST_Log_DB', true);
	@define('CONST_Log_File', false);
	@define('CONST_Log_File_Format', 'TODO'); // Currently hard coded
	@define('CONST_Log_File_SearchLog', '');
	@define('CONST_Log_File_ReverseLog', '');

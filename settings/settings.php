<?php
	if (file_exists(CONST_BasePath.'/settings/local.php')) require_once(CONST_BasePath.'/settings/local.php');
	if (isset($_GET['debug']) && $_GET['debug']) @define('CONST_Debug', true);

	// General settings
	@define('CONST_Debug', false);
	@define('CONST_Database_DSN', 'pgsql://@/nominatim'); // <driver>://<username>:<password>@<host>:<port>/<database>
	@define('CONST_Database_Web_User', 'www-data');
	@define('CONST_Max_Word_Frequency', '50000');
	@define('CONST_Limit_Reindexing', true);

	// Software versions
	@define('CONST_Postgresql_Version', '9.3'); // values: 9.0, ... , 9.4
	@define('CONST_Postgis_Version', '2.1'); // values: 1.5, 2.0, 2.1

	// Paths
	@define('CONST_Path_Postgresql_Contrib', '/usr/share/postgresql/'.CONST_Postgresql_Version.'/contrib');
	@define('CONST_Path_Postgresql_Postgis', CONST_Path_Postgresql_Contrib.'/postgis-'.CONST_Postgis_Version);
	@define('CONST_Osm2pgsql_Binary', CONST_BasePath.'/osm2pgsql/osm2pgsql');
	@define('CONST_Osmosis_Binary', '/usr/bin/osmosis');
	@define('CONST_Tiger_Data_Path', CONST_BasePath.'/data/tiger');

	// osm2pgsql settings
	@define('CONST_Osm2pgsql_Flatnode_File', null);

	// tablespace settings
	// osm2pgsql caching tables (aka slim mode tables) - update only
	@define('CONST_Tablespace_Osm2pgsql_Data', false);
	@define('CONST_Tablespace_Osm2pgsql_Index', false);
	// osm2pgsql output tables (aka main table) - update only
	@define('CONST_Tablespace_Place_Data', false);
	@define('CONST_Tablespace_Place_Index', false);
	// address computation tables - update only
	@define('CONST_Tablespace_Address_Data', false);
	@define('CONST_Tablespace_Address_Index', false);
	// search tables - needed for lookups
	@define('CONST_Tablespace_Search_Data', false);
	@define('CONST_Tablespace_Search_Index', false);
	// additional data, e.g. TIGER data, type searches - needed for lookups
	@define('CONST_Tablespace_Aux_Data', false);
	@define('CONST_Tablespace_Aux_Index', false);

	// Replication settings
	@define('CONST_Replication_Url', 'http://planet.openstreetmap.org/replication/minute');
	@define('CONST_Replication_MaxInterval', '3600');
	@define('CONST_Replication_Update_Interval', '60');  // How often upstream publishes diffs
	@define('CONST_Replication_Recheck_Interval', '60'); // How long to sleep if no update found yet

	// Connection buckets to rate limit people being nasty
	@define('CONST_ConnectionBucket_MemcacheServerAddress', false);
	@define('CONST_ConnectionBucket_MemcacheServerPort', 11211);
	@define('CONST_ConnectionBucket_MaxBlockList', 100);
	@define('CONST_ConnectionBucket_LeakRate', 1);
	@define('CONST_ConnectionBucket_BlockLimit', 10);
	@define('CONST_ConnectionBucket_WaitLimit', 6);
	@define('CONST_ConnectionBucket_MaxSleeping', 10);
	@define('CONST_ConnectionBucket_Cost_Reverse', 1);
	@define('CONST_ConnectionBucket_Cost_Search', 2);
	@define('CONST_ConnectionBucket_Cost_Details', 3);
	@define('CONST_ConnectionBucket_Cost_Status', 1);

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
	@define('CONST_NoAccessControl', true);
	@define('CONST_ClosedForIndexing', false);
	@define('CONST_ClosedForIndexingExceptionIPs', '');
	@define('CONST_BlockedIPs', '');
	@define('CONST_BulkUserIPs', '');
	@define('CONST_BlockMessage', ''); // additional info to show for blocked IPs

	@define('CONST_Website_BaseURL', 'http://'.php_uname('n').'/');
	@define('CONST_Tile_Default', 'Mapnik');

	@define('CONST_Default_Language', false);
	@define('CONST_Default_Lat', 20.0);
	@define('CONST_Default_Lon', 0.0);
	@define('CONST_Default_Zoom', 2);

	@define('CONST_Search_AreaPolygons_Enabled', true);
	@define('CONST_Search_AreaPolygons', true);

	@define('CONST_Search_BatchMode', false);

	@define('CONST_Search_TryDroppedAddressTerms', false);
	@define('CONST_Search_NameOnlySearchFrequencyThreshold', 500);

	// Set to zero to disable polygon output
	@define('CONST_PolygonOutput_MaximumTypes', 1);

	// Log settings
	@define('CONST_Log_DB', true);
	@define('CONST_Log_File', false);
	@define('CONST_Log_File_Format', 'TODO'); // Currently hard coded
	@define('CONST_Log_File_SearchLog', '');
	@define('CONST_Log_File_ReverseLog', '');

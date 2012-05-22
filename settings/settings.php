<?php
	if (file_exists(CONST_BasePath.'/settings/local.php')) require_once(CONST_BasePath.'/settings/local.php');
	if (isset($_GET['debug']) && $_GET['debug']) @define('CONST_Debug', true);

	// General settings
	@define('CONST_Debug', false);
	@define('CONST_Database_DSN', 'pgsql://@/nominatim');

	// Paths
	@define('CONST_Postgresql_Version', '9.1');
	@define('CONST_Path_Postgresql_Contrib', '/usr/share/postgresql/'.CONST_Postgresql_Version.'/contrib');
	@define('CONST_Path_Postgresql_Postgis', CONST_Path_Postgresql_Contrib.'/postgis-1.5');
	@define('CONST_Osm2pgsql_Binary', CONST_BasePath.'/osm2pgsql/osm2pgsql');
	@define('CONST_Osmosis_Binary', CONST_BasePath.'/osmosis-0.40.1/bin/osmosis');

	// Website settings
	@define('CONST_ClosedForIndexing', false);
	@define('CONST_ClosedForIndexingExceptionIPs', '');
	@define('CONST_BlockedIPs', '');

	@define('CONST_Website_BaseURL', 'http://'.php_uname('n').'/');
	@define('CONST_Tile_Default', 'Mapnik');

	@define('CONST_Default_Language', 'xx');
	@define('CONST_Default_Lat', 20.0);
	@define('CONST_Default_Lon', 0.0);
	@define('CONST_Default_Zoom', 2);

	@define('CONST_Search_AreaPolygons_Enabled', true);
	@define('CONST_Search_AreaPolygons', true);

	@define('CONST_Suggestions_Enabled', false);

	// Log settings
	@define('CONST_Log_DB', true);
	@define('CONST_Log_File', false);
	@define('CONST_Log_File_Format', 'TODO'); // Currently hard coded
	@define('CONST_Log_File_SearchLog', '');
	@define('CONST_Log_File_ReverseLog', '');

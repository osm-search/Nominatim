#!/usr/bin/php -Cq
<?php

	require_once(dirname(dirname(__FILE__)).'/lib/init-cmd.php');
	ini_set('memory_limit', '800M');

	$aCMDOptions = array(
		"Create and setup nominatim search system",
		array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
		array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
		array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

		array('osm-file', '', 0, 1, 1, 1, 'realpath', 'File to import'),
		array('threads', '', 0, 1, 1, 1, 'int', 'Number of threads (where possible)'),

		array('all', '', 0, 1, 0, 0, 'bool', 'Do the complete process'),

		array('create-db', '', 0, 1, 0, 0, 'bool', 'Create nominatim db'),
		array('setup-db', '', 0, 1, 0, 0, 'bool', 'Build a blank nominatim db'),
		array('import-data', '', 0, 1, 0, 0, 'bool', 'Import a osm file'),
		array('osm2pgsql-cache', '', 0, 1, 1, 1, 'int', 'Cache size used by osm2pgsql'),
		array('create-functions', '', 0, 1, 0, 0, 'bool', 'Create functions'),
		array('enable-diff-updates', '', 0, 1, 0, 0, 'bool', 'Turn on the code required to make diff updates work'),
		array('enable-debug-statements', '', 0, 1, 0, 0, 'bool', 'Include debug warning statements in pgsql commands'),
		array('ignore-errors', '', 0, 1, 0, 0, 'bool', 'Continue import even when errors in SQL are present (EXPERT)'),
		array('create-minimal-tables', '', 0, 1, 0, 0, 'bool', 'Create minimal main tables'),
		array('create-tables', '', 0, 1, 0, 0, 'bool', 'Create main tables'),
		array('create-partition-tables', '', 0, 1, 0, 0, 'bool', 'Create required partition tables'),
		array('create-partition-functions', '', 0, 1, 0, 0, 'bool', 'Create required partition triggers'),
		array('no-partitions', '', 0, 1, 0, 0, 'bool', "Do not partition search indices (speeds up import of single country extracts)"),
		array('import-wikipedia-articles', '', 0, 1, 0, 0, 'bool', 'Import wikipedia article dump'),
		array('load-data', '', 0, 1, 0, 0, 'bool', 'Copy data to live tables from import table'),
		array('disable-token-precalc', '', 0, 1, 0, 0, 'bool', 'Disable name precalculation (EXPERT)'),
		array('import-tiger-data', '', 0, 1, 0, 0, 'bool', 'Import tiger data (not included in \'all\')'),
		array('calculate-postcodes', '', 0, 1, 0, 0, 'bool', 'Calculate postcode centroids'),
		array('osmosis-init', '', 0, 1, 0, 0, 'bool', 'Generate default osmosis configuration'),
		array('index', '', 0, 1, 0, 0, 'bool', 'Index the data'),
		array('index-noanalyse', '', 0, 1, 0, 0, 'bool', 'Do not perform analyse operations during index (EXPERT)'),
		array('index-output', '', 0, 1, 1, 1, 'string', 'File to dump index information to'),
		array('create-search-indices', '', 0, 1, 0, 0, 'bool', 'Create additional indices required for search and update'),
		array('create-website', '', 0, 1, 1, 1, 'realpath', 'Create symlinks to setup web directory'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	$bDidSomething = false;

	// Check if osm-file is set and points to a valid file if --all or --import-data is given
	if ($aCMDResult['import-data'] || $aCMDResult['all'])
	{
		if (!isset($aCMDResult['osm-file']))
		{
			fail('missing --osm-file for data import');
		}

		if (!file_exists($aCMDResult['osm-file']))
		{
			fail('the path supplied to --osm-file does not exist');
		}

		if (!is_readable($aCMDResult['osm-file']))
		{
			fail('osm-file "'.$aCMDResult['osm-file'].'" not readable');
		}
	}


	// This is a pretty hard core default - the number of processors in the box - 1
	$iInstances = isset($aCMDResult['threads'])?$aCMDResult['threads']:(getProcessorCount()-1);
	if ($iInstances < 1)
	{
		$iInstances = 1;
		echo "WARNING: resetting threads to $iInstances\n";
	}
	if ($iInstances > getProcessorCount())
	{
		$iInstances = getProcessorCount();
		echo "WARNING: resetting threads to $iInstances\n";
	}

	// Assume we can steal all the cache memory in the box (unless told otherwise)
	$iCacheMemory = (isset($aCMDResult['osm2pgsql-cache'])?$aCMDResult['osm2pgsql-cache']:getCacheMemoryMB());
	if ($iCacheMemory > getTotalMemoryMB())
	{
		$iCacheMemory = getCacheMemoryMB();
		echo "WARNING: resetting cache memory to $iCacheMemory\n";
	}

	$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
	if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;

	$fPostgisVersion = (float) CONST_Postgis_Version;

	if ($aCMDResult['create-db'] || $aCMDResult['all'])
	{
		echo "Create DB\n";
		$bDidSomething = true;
		$oDB =& DB::connect(CONST_Database_DSN, false);
		if (!PEAR::isError($oDB))
		{
			fail('database already exists ('.CONST_Database_DSN.')');
		}
		passthruCheckReturn('createdb -E UTF-8 -p '.$aDSNInfo['port'].' '.$aDSNInfo['database']);
	}

	if ($aCMDResult['setup-db'] || $aCMDResult['all'])
	{
		echo "Setup DB\n";
		$bDidSomething = true;
		// TODO: path detection, detection memory, etc.

		$oDB =& getDB();

		$sVersionString = $oDB->getOne('select version()');
		preg_match('#PostgreSQL ([0-9]+)[.]([0-9]+)[^0-9]#', $sVersionString, $aMatches);
		if (CONST_Postgresql_Version != $aMatches[1].'.'.$aMatches[2])
		{
			echo "ERROR: PostgreSQL version is not correct.  Expected ".CONST_Postgresql_Version." found ".$aMatches[1].'.'.$aMatches[2]."\n";
			exit;
		}

		passthru('createlang plpgsql -p '.$aDSNInfo['port'].' '.$aDSNInfo['database']);
		$pgver = (float) CONST_Postgresql_Version;
		if ($pgver < 9.1) {
			pgsqlRunScriptFile(CONST_Path_Postgresql_Contrib.'/hstore.sql');
			pgsqlRunScriptFile(CONST_BasePath.'/sql/hstore_compatability_9_0.sql');
		} else {
			pgsqlRunScript('CREATE EXTENSION hstore');
		}

		if ($fPostgisVersion < 2.0) {
			pgsqlRunScriptFile(CONST_Path_Postgresql_Postgis.'/postgis.sql');
			pgsqlRunScriptFile(CONST_Path_Postgresql_Postgis.'/spatial_ref_sys.sql');
		} else {
			pgsqlRunScript('CREATE EXTENSION postgis');
		}
		if ($fPostgisVersion < 2.1) {
			// Function was renamed in 2.1 and throws an annoying deprecation warning
			pgsqlRunScript('ALTER FUNCTION st_line_interpolate_point(geometry, double precision) RENAME TO ST_LineInterpolatePoint');
		}
		$sVersionString = $oDB->getOne('select postgis_full_version()');
		preg_match('#POSTGIS="([0-9]+)[.]([0-9]+)[.]([0-9]+)( r([0-9]+))?"#', $sVersionString, $aMatches);
		if (CONST_Postgis_Version != $aMatches[1].'.'.$aMatches[2])
		{
			echo "ERROR: PostGIS version is not correct.  Expected ".CONST_Postgis_Version." found ".$aMatches[1].'.'.$aMatches[2]."\n";
			exit;
		}

		pgsqlRunScriptFile(CONST_BasePath.'/data/country_name.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/country_naturalearthdata.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/country_osm_grid.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode_table.sql');
		if (file_exists(CONST_BasePath.'/data/gb_postcode_data.sql.gz'))
		{
			pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode_data.sql.gz');
		}
		else
		{
			echo "WARNING: external UK postcode table not found.\n";
		}
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_statecounty.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_state.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_postcode.sql');

		if ($aCMDResult['no-partitions'])
		{
			pgsqlRunScript('update country_name set partition = 0');
		}

		// the following will be needed by create_functions later but
		// is only defined in the subsequently called create_tables.
		// Create dummies here that will be overwritten by the proper
		// versions in create-tables.
		pgsqlRunScript('CREATE TABLE place_boundingbox ()');
		pgsqlRunScript('create type wikipedia_article_match as ()');
	}

	if ($aCMDResult['import-data'] || $aCMDResult['all'])
	{
		echo "Import\n";
		$bDidSomething = true;

		$osm2pgsql = CONST_Osm2pgsql_Binary;
		if (!file_exists($osm2pgsql))
		{
			echo "Please download and build osm2pgsql.\nIf it is already installed, check the path in your local settings (settings/local.php) file.\n";
			fail("osm2pgsql not found in '$osm2pgsql'");
		}

		if (!is_null(CONST_Osm2pgsql_Flatnode_File))
		{
			$osm2pgsql .= ' --flat-nodes '.CONST_Osm2pgsql_Flatnode_File;
		}
		if (CONST_Tablespace_Osm2pgsql_Data)
			$osm2pgsql .= ' --tablespace-slim-data '.CONST_Tablespace_Osm2pgsql_Data;
		if (CONST_Tablespace_Osm2pgsql_Index)
			$osm2pgsql .= ' --tablespace-slim-index '.CONST_Tablespace_Osm2pgsql_Index;
		if (CONST_Tablespace_Place_Data)
			$osm2pgsql .= ' --tablespace-main-data '.CONST_Tablespace_Place_Data;
		if (CONST_Tablespace_Place_Index)
			$osm2pgsql .= ' --tablespace-main-index '.CONST_Tablespace_Place_Index;
		$osm2pgsql .= ' -lsc -O gazetteer --hstore';
		$osm2pgsql .= ' -C '.$iCacheMemory;
		$osm2pgsql .= ' -P '.$aDSNInfo['port'];
		$osm2pgsql .= ' -d '.$aDSNInfo['database'].' '.$aCMDResult['osm-file'];
		passthruCheckReturn($osm2pgsql);

		$oDB =& getDB();
		$x = $oDB->getRow('select * from place limit 1');
		if (PEAR::isError($x)) {
			fail($x->getMessage());
		}
		if (!$x) fail('No Data');
	}

	if ($aCMDResult['create-functions'] || $aCMDResult['all'])
	{
		echo "Functions\n";
		$bDidSomething = true;
		if (!file_exists(CONST_BasePath.'/module/nominatim.so')) fail("nominatim module not built");
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
		$sTemplate = str_replace('{modulepath}', CONST_BasePath.'/module', $sTemplate);
		if ($aCMDResult['enable-diff-updates']) $sTemplate = str_replace('RETURN NEW; -- @DIFFUPDATES@', '--', $sTemplate);
		if ($aCMDResult['enable-debug-statements']) $sTemplate = str_replace('--DEBUG:', '', $sTemplate);
		if (CONST_Limit_Reindexing) $sTemplate = str_replace('--LIMIT INDEXING:', '', $sTemplate);
		pgsqlRunScript($sTemplate);

		if ($fPostgisVersion < 2.0) {
			echo "Helper functions for postgis < 2.0\n";
			$sTemplate = file_get_contents(CONST_BasePath.'/sql/postgis_15_aux.sql');
		} else {
			echo "Helper functions for postgis >= 2.0\n";
			$sTemplate = file_get_contents(CONST_BasePath.'/sql/postgis_20_aux.sql');
		}
		pgsqlRunScript($sTemplate);
	}

	if ($aCMDResult['create-minimal-tables'])
	{
		echo "Minimal Tables\n";
		$bDidSomething = true;
		pgsqlRunScriptFile(CONST_BasePath.'/sql/tables-minimal.sql');

		$sScript = '';

		// Backstop the import process - easliest possible import id
		$sScript .= "insert into import_npi_log values (18022);\n";

		$hFile = @fopen(CONST_BasePath.'/settings/partitionedtags.def', "r");
		if (!$hFile) fail('unable to open list of partitions: '.CONST_BasePath.'/settings/partitionedtags.def');

		while (($sLine = fgets($hFile, 4096)) !== false && $sLine && substr($sLine,0,1) !='#')
		{
			list($sClass, $sType) = explode(' ', trim($sLine));
			$sScript .= "create table place_classtype_".$sClass."_".$sType." as ";
			$sScript .= "select place_id as place_id,geometry as centroid from placex limit 0;\n";

			$sScript .= "CREATE INDEX idx_place_classtype_".$sClass."_".$sType."_centroid ";
			$sScript .= "ON place_classtype_".$sClass."_".$sType." USING GIST (centroid);\n";

			$sScript .= "CREATE INDEX idx_place_classtype_".$sClass."_".$sType."_place_id ";
			$sScript .= "ON place_classtype_".$sClass."_".$sType." USING btree(place_id);\n";
		}
		fclose($hFile);
		pgsqlRunScript($sScript);
	}

	if ($aCMDResult['create-tables'] || $aCMDResult['all'])
	{
		$bDidSomething = true;

		echo "Tables\n";
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/tables.sql');
		$sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
		$sTemplate = replace_tablespace('{ts:address-data}',
		                                CONST_Tablespace_Address_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:address-index}',
		                                CONST_Tablespace_Address_Index, $sTemplate);
		$sTemplate = replace_tablespace('{ts:search-data}',
		                                CONST_Tablespace_Search_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:search-index}',
		                                CONST_Tablespace_Search_Index, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-data}',
		                                CONST_Tablespace_Aux_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-index}',
		                                CONST_Tablespace_Aux_Index, $sTemplate);
		pgsqlRunScript($sTemplate, false);

		// re-run the functions
		echo "Functions\n";
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
		$sTemplate = str_replace('{modulepath}',
			                     CONST_BasePath.'/module', $sTemplate);
		pgsqlRunScript($sTemplate);
	}

	if ($aCMDResult['create-partition-tables'] || $aCMDResult['all'])
	{
		echo "Partition Tables\n";
		$bDidSomething = true;
		$oDB =& getDB();
		$sSQL = 'select distinct partition from country_name';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		if (!$aCMDResult['no-partitions']) $aPartitions[] = 0;

		$sTemplate = file_get_contents(CONST_BasePath.'/sql/partition-tables.src.sql');
		$sTemplate = replace_tablespace('{ts:address-data}',
		                                CONST_Tablespace_Address_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:address-index}',
		                                CONST_Tablespace_Address_Index, $sTemplate);
		$sTemplate = replace_tablespace('{ts:search-data}',
		                                CONST_Tablespace_Search_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:search-index}',
		                                CONST_Tablespace_Search_Index, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-data}',
		                                CONST_Tablespace_Aux_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-index}',
		                                CONST_Tablespace_Aux_Index, $sTemplate);
		preg_match_all('#^-- start(.*?)^-- end#ms', $sTemplate, $aMatches, PREG_SET_ORDER);
		foreach($aMatches as $aMatch)
		{
			$sResult = '';
			foreach($aPartitions as $sPartitionName)
			{
				$sResult .= str_replace('-partition-', $sPartitionName, $aMatch[1]);
			}
			$sTemplate = str_replace($aMatch[0], $sResult, $sTemplate);
		}

		pgsqlRunScript($sTemplate);
	}


	if ($aCMDResult['create-partition-functions'] || $aCMDResult['all'])
	{
		echo "Partition Functions\n";
		$bDidSomething = true;
		$oDB =& getDB();
		$sSQL = 'select distinct partition from country_name';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		if (!$aCMDResult['no-partitions']) $aPartitions[] = 0;

		$sTemplate = file_get_contents(CONST_BasePath.'/sql/partition-functions.src.sql');
		preg_match_all('#^-- start(.*?)^-- end#ms', $sTemplate, $aMatches, PREG_SET_ORDER);
		foreach($aMatches as $aMatch)
		{
			$sResult = '';
			foreach($aPartitions as $sPartitionName)
			{
				$sResult .= str_replace('-partition-', $sPartitionName, $aMatch[1]);
			}
			$sTemplate = str_replace($aMatch[0], $sResult, $sTemplate);
		}

		pgsqlRunScript($sTemplate);
	}

	if ($aCMDResult['import-wikipedia-articles'] || $aCMDResult['all'])
	{
		$bDidSomething = true;
		$sWikiArticlesFile = CONST_BasePath.'/data/wikipedia_article.sql.bin';
		$sWikiRedirectsFile = CONST_BasePath.'/data/wikipedia_redirect.sql.bin';
		if (file_exists($sWikiArticlesFile))
		{
			echo "Importing wikipedia articles...";
			pgsqlRunDropAndRestore($sWikiArticlesFile);
			echo "...done\n";
		}
		else
		{
			echo "WARNING: wikipedia article dump file not found - places will have default importance\n";
		}
		if (file_exists($sWikiRedirectsFile))
		{
			echo "Importing wikipedia redirects...";
			pgsqlRunDropAndRestore($sWikiRedirectsFile);
			echo "...done\n";
		}
		else
		{
			echo "WARNING: wikipedia redirect dump file not found - some place importance values may be missing\n";
		}
	}


	if ($aCMDResult['load-data'] || $aCMDResult['all'])
	{
		echo "Drop old Data\n";
		$bDidSomething = true;

		$oDB =& getDB();
		if (!pg_query($oDB->connection, 'TRUNCATE word')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE placex')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE place_addressline')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE place_boundingbox')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE location_area')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE search_name')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE search_name_blank')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'DROP SEQUENCE seq_place')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'CREATE SEQUENCE seq_place start 100000')) fail(pg_last_error($oDB->connection));
		echo '.';

		$sSQL = 'select distinct partition from country_name';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		if (!$aCMDResult['no-partitions']) $aPartitions[] = 0;
		foreach($aPartitions as $sPartition)
		{
			if (!pg_query($oDB->connection, 'TRUNCATE location_road_'.$sPartition)) fail(pg_last_error($oDB->connection));
			echo '.';
		}

		// used by getorcreate_word_id to ignore frequent partial words
		if (!pg_query($oDB->connection, 'CREATE OR REPLACE FUNCTION get_maxwordfreq() RETURNS integer AS $$ SELECT '.CONST_Max_Word_Frequency.' as maxwordfreq; $$ LANGUAGE SQL IMMUTABLE')) fail(pg_last_error($oDB->connection));
		echo ".\n";

		// pre-create the word list
		if (!$aCMDResult['disable-token-precalc'])
		{
			echo "Loading word list\n";
			pgsqlRunScriptFile(CONST_BasePath.'/data/words.sql');
		}

		echo "Load Data\n";
		$aDBInstances = array();
		for($i = 0; $i < $iInstances; $i++)
		{
			$aDBInstances[$i] =& getDB(true);
			$sSQL = 'insert into placex (osm_type, osm_id, class, type, name, admin_level, ';
			$sSQL .= 'housenumber, street, addr_place, isin, postcode, country_code, extratags, ';
			$sSQL .= 'geometry) select * from place where osm_id % '.$iInstances.' = '.$i;
			if ($aCMDResult['verbose']) echo "$sSQL\n";
			if (!pg_send_query($aDBInstances[$i]->connection, $sSQL)) fail(pg_last_error($oDB->connection));
		}
		$bAnyBusy = true;
		while($bAnyBusy)
		{
			$bAnyBusy = false;
			for($i = 0; $i < $iInstances; $i++)
			{
				if (pg_connection_busy($aDBInstances[$i]->connection)) $bAnyBusy = true;
			}
			sleep(1);
			echo '.';
		}
		echo "\n";
		echo "Reanalysing database...\n";
		pgsqlRunScript('ANALYSE');
	}

	if ($aCMDResult['import-tiger-data'])
	{
		$bDidSomething = true;

		$sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_start.sql');
		$sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-data}',
		                                CONST_Tablespace_Aux_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-index}',
		                                CONST_Tablespace_Aux_Index, $sTemplate);
		pgsqlRunScript($sTemplate, false);

		$aDBInstances = array();
		for($i = 0; $i < $iInstances; $i++)
		{
			$aDBInstances[$i] =& getDB(true);
		}

		foreach(glob(CONST_BasePath.'/data/tiger2011/*.sql') as $sFile)
		{
			echo $sFile.': ';
			$hFile = fopen($sFile, "r");
			$sSQL = fgets($hFile, 100000);
			$iLines = 0;

			while(true)
			{
				for($i = 0; $i < $iInstances; $i++)
				{
					if (!pg_connection_busy($aDBInstances[$i]->connection))
					{
						while(pg_get_result($aDBInstances[$i]->connection));
						$sSQL = fgets($hFile, 100000);
						if (!$sSQL) break 2;
						if (!pg_send_query($aDBInstances[$i]->connection, $sSQL)) fail(pg_last_error($oDB->connection));
						$iLines++;
						if ($iLines == 1000)
						{
							echo ".";
							$iLines = 0;
						}
					}
				}
				usleep(10);
			}

			fclose($hFile);

			$bAnyBusy = true;
			while($bAnyBusy)
			{
				$bAnyBusy = false;
				for($i = 0; $i < $iInstances; $i++)
				{
					if (pg_connection_busy($aDBInstances[$i]->connection)) $bAnyBusy = true;
				}
				usleep(10);
			}
			echo "\n";
		}

		echo "Creating indexes\n";
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_finish.sql');
		$sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-data}',
		                                CONST_Tablespace_Aux_Data, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-index}',
		                                CONST_Tablespace_Aux_Index, $sTemplate);
		pgsqlRunScript($sTemplate, false);
	}

	if ($aCMDResult['calculate-postcodes'] || $aCMDResult['all'])
	{
		$bDidSomething = true;
		$oDB =& getDB();
		if (!pg_query($oDB->connection, 'DELETE from placex where osm_type=\'P\'')) fail(pg_last_error($oDB->connection));
		$sSQL = "insert into placex (osm_type,osm_id,class,type,postcode,calculated_country_code,geometry) ";
		$sSQL .= "select 'P',nextval('seq_postcodes'),'place','postcode',postcode,calculated_country_code,";
		$sSQL .= "ST_SetSRID(ST_Point(x,y),4326) as geometry from (select calculated_country_code,postcode,";
		$sSQL .= "avg(st_x(st_centroid(geometry))) as x,avg(st_y(st_centroid(geometry))) as y ";
		$sSQL .= "from placex where postcode is not null group by calculated_country_code,postcode) as x";
		if (!pg_query($oDB->connection, $sSQL)) fail(pg_last_error($oDB->connection));

		$sSQL = "insert into placex (osm_type,osm_id,class,type,postcode,calculated_country_code,geometry) ";
		$sSQL .= "select 'P',nextval('seq_postcodes'),'place','postcode',postcode,'us',";
		$sSQL .= "ST_SetSRID(ST_Point(x,y),4326) as geometry from us_postcode";
		if (!pg_query($oDB->connection, $sSQL)) fail(pg_last_error($oDB->connection));
	}

	if ($aCMDResult['osmosis-init'] || $aCMDResult['all'])
	{
		$bDidSomething = true;
		$oDB =& getDB();

		if (!file_exists(CONST_Osmosis_Binary))
		{
			echo "Please download osmosis.\nIf it is already installed, check the path in your local settings (settings/local.php) file.\n";
			if (!$aCMDResult['all'])
			{
				fail("osmosis not found in '".CONST_Osmosis_Binary."'");
			}
		}
		else
		{
			if (file_exists(CONST_BasePath.'/settings/configuration.txt'))
			{
				echo "settings/configuration.txt already exists\n";
			}
			else
			{
				passthru(CONST_Osmosis_Binary.' --read-replication-interval-init '.CONST_BasePath.'/settings');
				// update osmosis configuration.txt with our settings
				passthru("sed -i 's!baseUrl=.*!baseUrl=".CONST_Replication_Url."!' ".CONST_BasePath.'/settings/configuration.txt');
				passthru("sed -i 's:maxInterval = .*:maxInterval = ".CONST_Replication_MaxInterval.":' ".CONST_BasePath.'/settings/configuration.txt');
			}

			// Find the last node in the DB
			$iLastOSMID = $oDB->getOne("select max(osm_id) from place where osm_type = 'N'");

			// Lookup the timestamp that node was created (less 3 hours for margin for changsets to be closed)
			$sLastNodeURL = 'http://www.openstreetmap.org/api/0.6/node/'.$iLastOSMID."/1";
			$sLastNodeXML = file_get_contents($sLastNodeURL);
			preg_match('#timestamp="(([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z)"#', $sLastNodeXML, $aLastNodeDate);
			$iLastNodeTimestamp = strtotime($aLastNodeDate[1]) - (3*60*60);

			// Search for the correct state file - uses file timestamps so need to sort by date descending
			$sRepURL = CONST_Replication_Url."/";
			$sRep = file_get_contents($sRepURL."?C=M;O=D;F=1");
			// download.geofabrik.de:    <a href="000/">000/</a></td><td align="right">26-Feb-2013 11:53  </td>
			// planet.openstreetmap.org: <a href="273/">273/</a>                    2013-03-11 07:41    -
			preg_match_all('#<a href="[0-9]{3}/">([0-9]{3}/)</a>\s*([-0-9a-zA-Z]+ [0-9]{2}:[0-9]{2})#', $sRep, $aRepMatches, PREG_SET_ORDER);
			if ($aRepMatches)
			{
				$aPrevRepMatch = false;
				foreach($aRepMatches as $aRepMatch)
				{
					if (strtotime($aRepMatch[2]) < $iLastNodeTimestamp) break;
					$aPrevRepMatch = $aRepMatch;
				}
				if ($aPrevRepMatch) $aRepMatch = $aPrevRepMatch;

				$sRepURL .= $aRepMatch[1];
				$sRep = file_get_contents($sRepURL."?C=M;O=D;F=1");
				preg_match_all('#<a href="[0-9]{3}/">([0-9]{3}/)</a>\s*([-0-9a-zA-Z]+ [0-9]{2}:[0-9]{2})#', $sRep, $aRepMatches, PREG_SET_ORDER);
				$aPrevRepMatch = false;
				foreach($aRepMatches as $aRepMatch)
				{
					if (strtotime($aRepMatch[2]) < $iLastNodeTimestamp) break;
					$aPrevRepMatch = $aRepMatch;
				}
				if ($aPrevRepMatch) $aRepMatch = $aPrevRepMatch;

				$sRepURL .= $aRepMatch[1];
				$sRep = file_get_contents($sRepURL."?C=M;O=D;F=1");
				preg_match_all('#<a href="[0-9]{3}.state.txt">([0-9]{3}).state.txt</a>\s*([-0-9a-zA-Z]+ [0-9]{2}:[0-9]{2})#', $sRep, $aRepMatches, PREG_SET_ORDER);
				$aPrevRepMatch = false;
				foreach($aRepMatches as $aRepMatch)
				{
					if (strtotime($aRepMatch[2]) < $iLastNodeTimestamp) break;
					$aPrevRepMatch = $aRepMatch;
				}
				if ($aPrevRepMatch) $aRepMatch = $aPrevRepMatch;

				$sRepURL .= $aRepMatch[1].'.state.txt';
				echo "Getting state file: $sRepURL\n";
				$sStateFile = file_get_contents($sRepURL);
				if (!$sStateFile || strlen($sStateFile) > 1000) fail("unable to obtain state file");
				file_put_contents(CONST_BasePath.'/settings/state.txt', $sStateFile);
				echo "Updating DB status\n";
				pg_query($oDB->connection, 'TRUNCATE import_status');
				$sSQL = "INSERT INTO import_status VALUES('".$aRepMatch[2]."')";
				pg_query($oDB->connection, $sSQL);
			}
			else
			{
				if (!$aCMDResult['all'])
				{
					fail("Cannot read state file directory.");
				}
			}
		}
	}

	if ($aCMDResult['index'] || $aCMDResult['all'])
	{
		$bDidSomething = true;
		$sOutputFile = '';
		if (isset($aCMDResult['index-output'])) $sOutputFile = ' -F '.$aCMDResult['index-output'];
		$sBaseCmd = CONST_BasePath.'/nominatim/nominatim -i -d '.$aDSNInfo['database'].' -P '.$aDSNInfo['port'].' -t '.$iInstances.$sOutputFile;
		passthruCheckReturn($sBaseCmd.' -R 4');
		if (!$aCMDResult['index-noanalyse']) pgsqlRunScript('ANALYSE');
		passthruCheckReturn($sBaseCmd.' -r 5 -R 25');
		if (!$aCMDResult['index-noanalyse']) pgsqlRunScript('ANALYSE');
		passthruCheckReturn($sBaseCmd.' -r 26');
	}

	if ($aCMDResult['create-search-indices'] || $aCMDResult['all'])
	{
		echo "Search indices\n";
		$bDidSomething = true;
		$oDB =& getDB();
		$sSQL = 'select distinct partition from country_name';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		if (!$aCMDResult['no-partitions']) $aPartitions[] = 0;

		$sTemplate = file_get_contents(CONST_BasePath.'/sql/indices.src.sql');
		$sTemplate = replace_tablespace('{ts:address-index}',
		                                CONST_Tablespace_Address_Index, $sTemplate);
		$sTemplate = replace_tablespace('{ts:search-index}',
		                                CONST_Tablespace_Search_Index, $sTemplate);
		$sTemplate = replace_tablespace('{ts:aux-index}',
		                                CONST_Tablespace_Aux_Index, $sTemplate);
		preg_match_all('#^-- start(.*?)^-- end#ms', $sTemplate, $aMatches, PREG_SET_ORDER);
		foreach($aMatches as $aMatch)
		{
			$sResult = '';
			foreach($aPartitions as $sPartitionName)
			{
				$sResult .= str_replace('-partition-', $sPartitionName, $aMatch[1]);
			}
			$sTemplate = str_replace($aMatch[0], $sResult, $sTemplate);
		}

		pgsqlRunScript($sTemplate);
	}

	if (isset($aCMDResult['create-website']))
	{
		$bDidSomething = true;
		$sTargetDir = $aCMDResult['create-website'];
		if (!is_dir($sTargetDir))
		{
			echo "You must create the website directory before calling this function.\n";
			fail("Target directory does not exist.");
		}

		@symlink(CONST_BasePath.'/website/details.php', $sTargetDir.'/details.php');
		@symlink(CONST_BasePath.'/website/reverse.php', $sTargetDir.'/reverse.php');
		@symlink(CONST_BasePath.'/website/search.php', $sTargetDir.'/search.php');
		@symlink(CONST_BasePath.'/website/search.php', $sTargetDir.'/index.php');
		@symlink(CONST_BasePath.'/website/deletable.php', $sTargetDir.'/deletable.php');
		@symlink(CONST_BasePath.'/website/polygons.php', $sTargetDir.'/polygons.php');
		@symlink(CONST_BasePath.'/website/status.php', $sTargetDir.'/status.php');
		@symlink(CONST_BasePath.'/website/images', $sTargetDir.'/images');
		@symlink(CONST_BasePath.'/website/js', $sTargetDir.'/js');
		@symlink(CONST_BasePath.'/website/css', $sTargetDir.'/css');
		echo "Symlinks created\n";

		$sTestFile = @file_get_contents(CONST_Website_BaseURL.'js/tiles.js');
		if (!$sTestFile)
		{
			echo "\nWARNING: Unable to access the website at ".CONST_Website_BaseURL."\n";
			echo "You may want to update settings/local.php with @define('CONST_Website_BaseURL', 'http://[HOST]/[PATH]/');\n";
		}
	}

	if (!$bDidSomething)
	{
		showUsage($aCMDOptions, true);
	}
	else
	{
		echo "Setup finished.\n";
	}

	function pgsqlRunScriptFile($sFilename)
	{
		if (!file_exists($sFilename)) fail('unable to find '.$sFilename);

		// Convert database DSN to psql parameters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
		$sCMD = 'psql -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'];

		$ahGzipPipes = null;
		if (preg_match('/\\.gz$/', $sFilename))
		{
			$aDescriptors = array(
				0 => array('pipe', 'r'),
				1 => array('pipe', 'w'),
				2 => array('file', '/dev/null', 'a')
			);
			$hGzipProcess = proc_open('zcat '.$sFilename, $aDescriptors, $ahGzipPipes);
			if (!is_resource($hGzipProcess)) fail('unable to start zcat');
			$aReadPipe = $ahGzipPipes[1];
			fclose($ahGzipPipes[0]);
		}
		else
		{
			$sCMD .= ' -f '.$sFilename;
			$aReadPipe = array('pipe', 'r');
		}

		$aDescriptors = array(
			0 => $aReadPipe,
			1 => array('pipe', 'w'),
			2 => array('file', '/dev/null', 'a')
		);
		$ahPipes = null;
		$hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
		if (!is_resource($hProcess)) fail('unable to start pgsql');


		// TODO: error checking
		while(!feof($ahPipes[1]))
		{
			echo fread($ahPipes[1], 4096);
		}
		fclose($ahPipes[1]);

		$iReturn = proc_close($hProcess);
		if ($iReturn > 0)
		{
			fail("pgsql returned with error code ($iReturn)");
		}
		if ($ahGzipPipes)
		{
			fclose($ahGzipPipes[1]);
			proc_close($hGzipProcess);
		}

	}

	function pgsqlRunScript($sScript, $bfatal = true)
	{
		global $aCMDResult;
		// Convert database DSN to psql parameters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
		$sCMD = 'psql -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'];
		if ($bfatal && !$aCMDResult['ignore-errors'])
			$sCMD .= ' -v ON_ERROR_STOP=1';
		$aDescriptors = array(
			0 => array('pipe', 'r'),
			1 => STDOUT, 
			2 => STDERR
		);
		$ahPipes = null;
		$hProcess = @proc_open($sCMD, $aDescriptors, $ahPipes);
		if (!is_resource($hProcess)) fail('unable to start pgsql');

		while(strlen($sScript))
		{
			$written = fwrite($ahPipes[0], $sScript);
			if ($written <= 0) break;
			$sScript = substr($sScript, $written);
		}
		fclose($ahPipes[0]);
		$iReturn = proc_close($hProcess);
		if ($bfatal && $iReturn > 0)
		{
			fail("pgsql returned with error code ($iReturn)");
		}
	}

	function pgsqlRunRestoreData($sDumpFile)
	{
		// Convert database DSN to psql parameters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
		$sCMD = 'pg_restore -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'].' -Fc -a '.$sDumpFile;

		$aDescriptors = array(
			0 => array('pipe', 'r'),
			1 => array('pipe', 'w'),
			2 => array('file', '/dev/null', 'a')
		);
		$ahPipes = null;
		$hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
		if (!is_resource($hProcess)) fail('unable to start pg_restore');

		fclose($ahPipes[0]);

		// TODO: error checking
		while(!feof($ahPipes[1]))
		{
			echo fread($ahPipes[1], 4096);
		}
		fclose($ahPipes[1]);

		$iReturn = proc_close($hProcess);
	}

	function pgsqlRunDropAndRestore($sDumpFile)
	{
		// Convert database DSN to psql parameters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
		$sCMD = 'pg_restore -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'].' -Fc --clean '.$sDumpFile;

		$aDescriptors = array(
			0 => array('pipe', 'r'),
			1 => array('pipe', 'w'),
			2 => array('file', '/dev/null', 'a')
		);
		$ahPipes = null;
		$hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
		if (!is_resource($hProcess)) fail('unable to start pg_restore');

		fclose($ahPipes[0]);

		// TODO: error checking
		while(!feof($ahPipes[1]))
		{
			echo fread($ahPipes[1], 4096);
		}
		fclose($ahPipes[1]);

		$iReturn = proc_close($hProcess);
	}

	function passthruCheckReturn($cmd)
	{
		$result = -1;
		passthru($cmd, $result);
		if ($result != 0) fail('Error executing external command: '.$cmd);
	}

	function replace_tablespace($sTemplate, $sTablespace, $sSql)
	{
		if ($sTablespace)
			$sSql = str_replace($sTemplate, 'TABLESPACE "'.$sTablespace.'"',
			                    $sSql);
		else
			$sSql = str_replace($sTemplate, '', $sSql);

		return $sSql;
	}


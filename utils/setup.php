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
		array('create-minimal-tables', '', 0, 1, 0, 0, 'bool', 'Create minimal main tables'),
		array('create-tables', '', 0, 1, 0, 0, 'bool', 'Create main tables'),
		array('create-partitions', '', 0, 1, 0, 0, 'bool', 'Create required partition tables and triggers'),
		array('import-wikipedia-articles', '', 0, 1, 0, 0, 'bool', 'Import wikipedia article dump'),
		array('load-data', '', 0, 1, 0, 0, 'bool', 'Copy data to live tables from import table'),
		array('disable-token-precalc', '', 0, 1, 0, 0, 'bool', 'Disable name precalculation (EXPERT)'),
		array('import-tiger-data', '', 0, 1, 0, 0, 'bool', 'Import tiger data (not included in \'all\')'),
		array('calculate-postcodes', '', 0, 1, 0, 0, 'bool', 'Calculate postcode centroids'),
		array('create-roads', '', 0, 1, 0, 0, 'bool', 'Calculate postcode centroids'),
		array('osmosis-init', '', 0, 1, 0, 0, 'bool', 'Generate default osmosis configuration'),
		array('osmosis-init-date', '', 0, 1, 1, 1, 'string', 'Generate default osmosis configuration'),
		array('index', '', 0, 1, 0, 0, 'bool', 'Index the data'),
		array('index-noanalyse', '', 0, 1, 0, 0, 'bool', 'Do not perform analyse operations during index (EXPERT)'),
		array('index-output', '', 0, 1, 1, 1, 'string', 'File to dump index information to'),
		array('create-search-indices', '', 0, 1, 0, 0, 'bool', 'Create additional indices required for search and update'),
		array('create-website', '', 0, 1, 1, 1, 'realpath', 'Create symlinks to setup web directory'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	$bDidSomething = false;

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

	if (isset($aCMDResult['osm-file']) && !isset($aCMDResult['osmosis-init-date']))
	{
		$sBaseFile = basename($aCMDResult['osm-file']);
		if (preg_match('#^planet-([0-9]{2})([0-9]{2})([0-9]{2})[.]#', $sBaseFile, $aMatch))
		{
			$iTime = mktime(0, 0, 0, $aMatch[2], $aMatch[3], '20'.$aMatch[1]);
			$iTime -= (60*60*24);
			$aCMDResult['osmosis-init-date'] = date('Y-m-d', $iTime).'T22:00:00Z';
		}
	}
	$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
	if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;

	if ($aCMDResult['create-db'] || $aCMDResult['all'])
	{
		echo "Create DB\n";
		$bDidSomething = true;
		$oDB =& DB::connect(CONST_Database_DSN, false);
		if (!PEAR::isError($oDB))
		{
			fail('database already exists ('.CONST_Database_DSN.')');
		}
		passthru('createdb -E UTF-8 '.$aDSNInfo['database']);
	}

	if ($aCMDResult['create-db'] || $aCMDResult['all'])
	{
		echo "Create DB (2)\n";
		$bDidSomething = true;
		// TODO: path detection, detection memory, etc.

		$oDB =& getDB();
		passthru('createlang plpgsql '.$aDSNInfo['database']);
		$pgver = (float) CONST_Postgresql_Version;
		if ($pgver < 9.1) {
			pgsqlRunScriptFile(CONST_Path_Postgresql_Contrib.'/hstore.sql');
		} else {
			pgsqlRunScript('CREATE EXTENSION hstore');
		}
		pgsqlRunScriptFile(CONST_Path_Postgresql_Postgis.'/postgis.sql');
		pgsqlRunScriptFile(CONST_Path_Postgresql_Postgis.'/spatial_ref_sys.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/country_name.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/country_naturalearthdata.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/country_osm_grid.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_statecounty.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_state.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_postcode.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/worldboundaries.sql');
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
		$osm2pgsql .= ' -lsc -O gazetteer --hstore';
		$osm2pgsql .= ' -C '.$iCacheMemory;
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
		echo "Tables\n";
		$bDidSomething = true;
		pgsqlRunScriptFile(CONST_BasePath.'/sql/tables.sql');

		// re-run the functions
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
		$sTemplate = str_replace('{modulepath}',CONST_BasePath.'/module', $sTemplate);
		pgsqlRunScript($sTemplate);
	}

	if ($aCMDResult['create-partitions'] || $aCMDResult['all'])
	{
		echo "Partitions\n";
		$bDidSomething = true;
		$oDB =& getDB();
		$sSQL = 'select partition from country_name order by country_code';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		$aPartitions[] = 0;

		$sTemplate = file_get_contents(CONST_BasePath.'/sql/partitions.src.sql');
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
		echo "Load Data\n";
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

		$sSQL = 'select partition from country_name order by country_code';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		$aPartitions[] = 0;
		foreach($aPartitions as $sPartition)
		{
			if (!pg_query($oDB->connection, 'TRUNCATE location_road_'.$sPartition)) fail(pg_last_error($oDB->connection));
			echo '.';
		}

		// pre-create the word list
		if (!$aCMDResult['disable-token-precalc'])
		{
			if (!pg_query($oDB->connection, 'select count(make_keywords(v)) from (select distinct svals(name) as v from place) as w where v is not null;')) fail(pg_last_error($oDB->connection));
			echo '.';
			if (!pg_query($oDB->connection, 'select count(make_keywords(v)) from (select distinct postcode as v from place) as w where v is not null;')) fail(pg_last_error($oDB->connection));
			echo '.';
			if (!pg_query($oDB->connection, 'select count(getorcreate_housenumber_id(v)) from (select distinct housenumber as v from place where housenumber is not null) as w;')) fail(pg_last_error($oDB->connection));
			echo '.';
		}

		$aDBInstances = array();
		for($i = 0; $i < $iInstances; $i++)
		{
			$aDBInstances[$i] =& getDB(true);
			$sSQL = 'insert into placex (osm_type, osm_id, class, type, name, admin_level, ';
			$sSQL .= 'housenumber, street, isin, postcode, country_code, extratags, ';
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

	if ($aCMDResult['create-roads'])
	{
		$bDidSomething = true;

		$oDB =& getDB();
		$aDBInstances = array();
		for($i = 0; $i < $iInstances; $i++)
		{
			$aDBInstances[$i] =& getDB(true);
			if (!pg_query($aDBInstances[$i]->connection, 'set enable_bitmapscan = off')) fail(pg_last_error($oDB->connection));
			$sSQL = 'select count(*) from (select insertLocationRoad(partition, place_id, country_code, geometry) from ';
			$sSQL .= 'placex where osm_id % '.$iInstances.' = '.$i.' and rank_search between 26 and 27 and class = \'highway\') as x ';
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
	}

	if ($aCMDResult['import-tiger-data'])
	{
		$bDidSomething = true;

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
	}

	if ($aCMDResult['calculate-postcodes'] || $aCMDResult['all'])
	{
		$bDidSomething = true;
		$oDB =& getDB();
		if (!pg_query($oDB->connection, 'DELETE from placex where osm_type=\'P\'')) fail(pg_last_error($oDB->connection));
		$sSQL = "insert into placex (osm_type,osm_id,class,type,postcode,country_code,geometry) ";
		$sSQL .= "select 'P',nextval('seq_postcodes'),'place','postcode',postcode,country_code,";
		$sSQL .= "ST_SetSRID(ST_Point(x,y),4326) as geometry from (select country_code,postcode,";
		$sSQL .= "avg(st_x(st_centroid(geometry))) as x,avg(st_y(st_centroid(geometry))) as y ";
		$sSQL .= "from placex where postcode is not null group by country_code,postcode) as x";
		if (!pg_query($oDB->connection, $sSQL)) fail(pg_last_error($oDB->connection));

		$sSQL = "insert into placex (osm_type,osm_id,class,type,postcode,country_code,geometry) ";
		$sSQL .= "select 'P',nextval('seq_postcodes'),'place','postcode',postcode,'us',";
		$sSQL .= "ST_SetSRID(ST_Point(x,y),4326) as geometry from us_postcode";
		if (!pg_query($oDB->connection, $sSQL)) fail(pg_last_error($oDB->connection));
	}

	if (($aCMDResult['osmosis-init'] || $aCMDResult['all']) && isset($aCMDResult['osmosis-init-date']))
	{
		$bDidSomething = true;
		$oDB =& getDB();

		if (!file_exists(CONST_Osmosis_Binary)) fail("please download osmosis");
		if (file_exists(CONST_BasePath.'/settings/configuration.txt')) echo "settings/configuration.txt already exists\n";
		else passthru(CONST_Osmosis_Binary.' --read-replication-interval-init '.CONST_BasePath.'/settings');

		$sDate = $aCMDResult['osmosis-init-date'];
		$aDate = date_parse_from_format("Y-m-d\TH-i", $sDate);
		$sURL = 'http://toolserver.org/~mazder/replicate-sequences/?';
		$sURL .= 'Y='.$aDate['year'].'&m='.$aDate['month'].'&d='.$aDate['day'];
		$sURL .= '&H='.$aDate['hour'].'&i='.$aDate['minute'].'&s=0';
		$sURL .= '&stream=minute';
		echo "Getting state file: $sURL\n";
		$sStateFile = file_get_contents($sURL);
		if (!$sStateFile || strlen($sStateFile) > 1000) fail("unable to obtain state file");
		file_put_contents(CONST_BasePath.'/settings/state.txt', $sStateFile);
		echo "Updating DB status\n";
		pg_query($oDB->connection, 'TRUNCATE import_status');
		$sSQL = "INSERT INTO import_status VALUES('".$sDate."')";
		pg_query($oDB->connection, $sSQL);

	}

	if ($aCMDResult['index'] || $aCMDResult['all'])
	{
		$bDidSomething = true;
		$sOutputFile = '';
		if (isset($aCMDResult['index-output'])) $sOutputFile = ' -F '.$aCMDResult['index-output'];
		$sBaseCmd = CONST_BasePath.'/nominatim/nominatim -i -d '.$aDSNInfo['database'].' -t '.$iInstances.$sOutputFile;
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
		$sSQL = 'select partition from country_name order by country_code';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		$aPartitions[] = 0;

		$sTemplate = file_get_contents(CONST_BasePath.'/sql/indices.src.sql');
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
		@symlink(CONST_BasePath.'/website/images', $sTargetDir.'/images');
		@symlink(CONST_BasePath.'/website/js', $sTargetDir.'/js');
		echo "Symlinks created\n";
	}

	if (!$bDidSomething)
	{
		showUsage($aCMDOptions, true);
	}

	function pgsqlRunScriptFile($sFilename)
	{
		if (!file_exists($sFilename)) fail('unable to find '.$sFilename);

		// Convert database DSN to psql parameters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
		$sCMD = 'psql -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'].' -f '.$sFilename;

		$aDescriptors = array(
			0 => array('pipe', 'r'),
			1 => array('pipe', 'w'),
			2 => array('file', '/dev/null', 'a')
		);
		$ahPipes = null;
		$hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
		if (!is_resource($hProcess)) fail('unable to start pgsql');

		fclose($ahPipes[0]);

		// TODO: error checking
		while(!feof($ahPipes[1]))
		{
			echo fread($ahPipes[1], 4096);
		}
		fclose($ahPipes[1]);

		proc_close($hProcess);
	}

	function pgsqlRunScript($sScript)
	{
		// Convert database DSN to psql parameters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
		$sCMD = 'psql -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'];
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
			$sScript = substr($sScript, $written);
		}
		fclose($ahPipes[0]);
		proc_close($hProcess);
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

		proc_close($hProcess);
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

		proc_close($hProcess);
	}

	function passthruCheckReturn($cmd)
	{
		$result = -1;
		passthru($cmd, $result);
		if ($result != 0) fail('Error executing external command: '.$cmd);
	}

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
		array('create-functions', '', 0, 1, 0, 0, 'bool', 'Create functions'),
		array('create-tables', '', 0, 1, 0, 0, 'bool', 'Create main tables'),
		array('create-partitions', '', 0, 1, 0, 0, 'bool', 'Create required partition tables and triggers'),
		array('load-data', '', 0, 1, 0, 0, 'bool', 'Copy data to live tables from import table'),
		array('import-tiger-data', '', 0, 1, 0, 0, 'bool', 'Import tiger data (not included in \'all\')'),
		array('calculate-postcodes', '', 0, 1, 0, 0, 'bool', 'Calculate postcode centroids'),
		array('create-roads', '', 0, 1, 0, 0, 'bool', 'Calculate postcode centroids'),
		array('osmosis-init', '', 0, 1, 0, 0, 'bool', 'Generate default osmosis configuration'),
		array('osmosis-init-date', '', 0, 1, 1, 1, 'string', 'Generate default osmosis configuration'),
		array('index', '', 0, 1, 0, 0, 'bool', 'Index the data'),
		array('index-output', '', 0, 1, 1, 1, 'string', 'File to dump index information to'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	$bDidSomething = false;

	// This is a pretty hard core defult - the number of processors in the box - 1
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

	if ($aCMDResult['create-db'] || $aCMDResult['all'])
	{
		echo "Create DB\n";
		$bDidSomething = true;
		$oDB =& DB::connect(CONST_Database_DSN, false);
		if (!PEAR::isError($oDB))
		{
			fail('database already exists');
		}
		passthru('createdb nominatim');
	}

	if ($aCMDResult['create-db'] || $aCMDResult['all'])
	{
		echo "Create DB (2)\n";
		$bDidSomething = true;
		// TODO: path detection, detection memory, etc.

		$oDB =& getDB();
		passthru('createlang plpgsql nominatim');
		pgsqlRunScriptFile(CONST_Path_Postgresql_Contrib.'/_int.sql');
		pgsqlRunScriptFile(CONST_Path_Postgresql_Contrib.'/hstore.sql');
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

		if (!file_exists(CONST_BasePath.'/osm2pgsql/osm2pgsql')) fail("please download and build osm2pgsql");
		passthru(CONST_BasePath.'/osm2pgsql/osm2pgsql -lsc -O gazetteer -C 10000 --hstore -d nominatim '.$aCMDResult['osm-file']);

		$oDB =& getDB();
		$x = $oDB->getRow('select * from place limit 1');
		if (!$x || PEAR::isError($x)) fail('No Data');
	}

	if ($aCMDResult['create-functions'] || $aCMDResult['all'])
	{
		echo "Functions\n";
		$bDidSomething = true;
		if (!file_exists(CONST_BasePath.'/module/nominatim.so')) fail("nominatim module not built");
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
		$sTemplate = str_replace('{modulepath}',CONST_BasePath.'/module', $sTemplate);
		pgsqlRunScript($sTemplate);
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

		foreach(glob(CONST_BasePath.'/data/tiger2009/*.sql') as $sFile)
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

		if (!file_exists(CONST_BasePath.'/osmosis-0.38/bin/osmosis')) fail("please download osmosis");
		if (file_exists(CONST_BasePath.'/settings/configuration.txt')) echo "settings/configuration.txt already exists\n";
		else passthru(CONST_BasePath.'/osmosis-0.38/bin/osmosis --read-replication-interval-init '.CONST_BasePath.'/settings');

		$sDate = $aCMDResult['osmosis-init-date'];
		$sURL = 'http://toolserver.org/~mazder/replicate-sequences/?'.$sDate;
		echo "Getting state file: $sURL\n";
		$sStateFile = file_get_contents($sURL);
		if (!$sStateFile || strlen($sStateFile) > 1000) fail("unable to obtain state file");
		file_put_contents(CONST_BasePath.'/settings/state.txt', $sStateFile);
	}

	if ($aCMDResult['index'] || $aCMDResult['all'])
	{
		$bDidSomething = true;
		$sOutputFile = '';
		if (isset($aCMDResult['index-output'])) $sOutputFile = ' -F '.$aCMDResult['index-output'];
		passthru(CONST_BasePath.'/nominatim/nominatim -i -d nominatim -t '.$iInstances.$sOutputFile);
	}

	if (!$bDidSomething)
	{
		showUsage($aCMDOptions, true);
	}

	function pgsqlRunScriptFile($sFilename)
	{
		if (!file_exists($sFilename)) fail('unable to find '.$sFilename);

		// Convert database DSN to psql paramaters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		$sCMD = 'psql -f '.$sFilename.' '.$aDSNInfo['database'];

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
		// Convert database DSN to psql paramaters
		$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
		if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
		$sCMD = 'psql -p '.$aDSNInfo['port'].' '.$aDSNInfo['database'];
		$aDescriptors = array(
			0 => array('pipe', 'r'),
			1 => array('pipe', 'w'),
			2 => array('file', '/dev/null', 'a')
		);
		$ahPipes = null;
		$hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
		if (!is_resource($hProcess)) fail('unable to start pgsql');

		fwrite($ahPipes[0], $sScript);
		fclose($ahPipes[0]);

		// TODO: error checking
		while(!feof($ahPipes[1]))
		{
			echo fread($ahPipes[1], 4096);
		}
		fclose($ahPipes[1]);

		proc_close($hProcess);
	}

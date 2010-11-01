#!/usr/bin/php -Cq
<?php

	require_once(dirname(dirname(__FILE__)).'/lib/init-cmd.php');
	ini_set('memory_limit', '800M');

	$aCMDOptions = array(
		"Create and setup nominatim search system",
		array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
		array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
		array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

		array('all', '', 0, 1, 1, 1, 'realpath', 'Do the complete process'),

		array('create-db', '', 0, 1, 0, 0, 'bool', 'Create nominatim db'),
		array('setup-db', '', 0, 1, 0, 0, 'bool', 'Build a blank nominatim db'),
		array('import-data', '', 0, 1, 1, 1, 'realpath', 'Import a osm file'),
		array('create-functions', '', 0, 1, 0, 0, 'bool', 'Create functions'),
		array('create-tables', '', 0, 1, 0, 0, 'bool', 'Create main tables'),
		array('create-partitions', '', 0, 1, 0, 0, 'bool', 'Create required partition tables and triggers'),
		array('load-data', '', 0, 1, 0, 0, 'bool', 'Copy data to live tables from import table'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	$bDidSomething = false;

	if ($aCMDResult['create-db'] || isset($aCMDResult['all']))
	{
		$bDidSomething = true;
		$oDB =& DB::connect(CONST_Database_DSN, false);
		if (!PEAR::isError($oDB))
		{
			fail('database already exists');
		}
		passthru('createdb nominatim');
	}

	if ($aCMDResult['create-db'] || isset($aCMDResult['all']))
	{
		$bDidSomething = true;
		// TODO: path detection, detection memory, etc.

		$oDB =& getDB();
		passthru('createlang plpgsql nominatim');
		pgsqlRunScriptFile(CONST_Path_Postgresql_Contrib.'/_int.sql');
		pgsqlRunScriptFile(CONST_Path_Postgresql_Contrib.'/hstore.sql');
		pgsqlRunScriptFile(CONST_Path_Postgresql_Postgis.'/postgis.sql');
		pgsqlRunScriptFile(CONST_Path_Postgresql_Postgis.'/spatial_ref_sys.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/country_name.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/country_osm_grid.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_statecounty.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/us_state.sql');
		pgsqlRunScriptFile(CONST_BasePath.'/data/worldboundaries.sql');
	}

	if (isset($aCMDResult['all']) && !isset($aCMDResult['import-data'])) $aCMDResult['import-data'] = $aCMDResult['all'];
	if (isset($aCMDResult['import-data']) && $aCMDResult['import-data'])
	{
		$bDidSomething = true;
		passthru(CONST_BasePath.'/osm2pgsql/osm2pgsql -lsc -O gazetteer -C 10000 --hstore -d nominatim '.$aCMDResult['import-data']);
	}

	if ($aCMDResult['create-functions'] || isset($aCMDResult['all']))
	{
		$bDidSomething = true;
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
		$sTemplate = str_replace('{modulepath}',CONST_BasePath.'/module', $sTemplate);
		pgsqlRunScript($sTemplate);
	}

	if ($aCMDResult['create-tables'] || isset($aCMDResult['all']))
	{
		$bDidSomething = true;
		pgsqlRunScriptFile(CONST_BasePath.'/sql/tables.sql');

		// re-run the functions
		$sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
		$sTemplate = str_replace('{modulepath}',CONST_BasePath.'/module', $sTemplate);
		pgsqlRunScript($sTemplate);
	}

	if ($aCMDResult['create-partitions'] || isset($aCMDResult['all']))
	{
		$bDidSomething = true;
		$oDB =& getDB();
		$sSQL = 'select distinct country_code from country_name order by country_code';
		$aPartitions = $oDB->getCol($sSQL);
		if (PEAR::isError($aPartitions))
		{
			fail($aPartitions->getMessage());
		}
		$aPartitions[] = 'none';

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

	if ($aCMDResult['load-data'] || isset($aCMDResult['all']))
	{
		$bDidSomething = true;

		$oDB =& getDB();
		if (!pg_query($oDB->connection, 'TRUNCATE placex')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE place_addressline')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'TRUNCATE location_area')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'DROP SEQUENCE seq_place')) fail(pg_last_error($oDB->connection));
		echo '.';
		if (!pg_query($oDB->connection, 'CREATE SEQUENCE seq_place start 100000')) fail(pg_last_error($oDB->connection));
		echo '.';

		$iInstances = 16;
		$aDBInstances = array();
		for($i = 0; $i < $iInstances; $i++)
		{
			$aDBInstances[$i] =& getDB(true);
			$sSQL = 'insert into placex (osm_type, osm_id, class, type, name, admin_level, ';
			$sSQL .= 'housenumber, street, isin, postcode, country_code, extratags, ';
			$sSQL .= 'geometry) select * from place where osm_id % '.$iInstances.' = '.$i;
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
		$sCMD = 'psql '.$aDSNInfo['database'];

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

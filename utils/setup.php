#!/usr/bin/php -Cq
<?php

	require_once(dirname(dirname(__FILE__)).'/lib/init-cmd.php');
	ini_set('memory_limit', '800M');

	$aCMDOptions = array(
		"Create and setup nominatim search system",
		array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
		array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
		array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

		array('create-db', '', 0, 1, 0, 0, 'bool', 'Build a blank nominatim db'),
		array('load-data', '', 0, 1, 0, 0, 'realpath', 'Import a osm file'),
		array('create-partitions', '', 0, 1, 0, 0, 'bool', 'Create required partition tables and triggers'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	if ($aCMDResult['create-db'])
	{
		// TODO: path detection, detection memory, etc.
		passthru('createdb nominatim');
		passthru('createlang plpgsql nominatim');
		passthru('psql -f /mqdata/mapquest/postgres-9.0.1-server/share/contrib/_int.sql nominatim');
		passthru('psql -f /mqdata/mapquest/postgres-9.0.1-server/share/contrib/hstore.sql nominatim');
		passthru('psql -f /mqdata/mapquest/postgres-9.0.1-server/share/contrib/postgis-1.5/postgis.sql nominatim');
		passthru('psql -f /mqdata/mapquest/postgres-9.0.1-server/share/contrib/postgis-1.5/spatial_ref_sys.sql nominatim');
	}

	if ($aCMDResult['load-data'])
	{
		passthru(CONST_BasePath.'/osm2pgsql -lsc -O gazetteer -C 10000 --hstore -d nominatim '.$aCMDResult['load-data']);
	}

	if ($aCMDResult['create-partitions'])
	{
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
		echo $sTemplate;
		exit;
	}

	showUsage($aCMDOptions, true);

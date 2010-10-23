#!/usr/bin/php -Cq
<?php

	require_once('../lib/init-cmd.php');
	ini_set('memory_limit', '800M');

	$aCMDOptions = array(
		"Create and setup nominatim search system",
		array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
		array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
		array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

		array('create-partitions', '', 0, 1, 0, 0, 'bool', 'Create required partition tables and triggers'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	if ($aCMDResult['create-partitions'])
	{
		$sSQL = 'select distinct country_code from country_name order by country_code';
		$aPartitions = $oDB->getCol($sSQL);
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
	}

	showUsage($aCMDOptions, true);

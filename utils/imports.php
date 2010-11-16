#!/usr/bin/php -Cq
<?php

	require_once(dirname(dirname(__FILE__)).'/lib/init-cmd.php');
	ini_set('memory_limit', '800M');

	$aCMDOptions = array(
		"Create and setup nominatim search system",
		array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
		array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
		array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

		array('parse-tiger', '', 0, 1, 1, 1, 'realpath', 'Convert tigger edge files to nominatim sql import'),
	);
	getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	$bDidSomething = false;

	if (isset($aCMDResult['parse-tiger']))
	{
		$sTempDir = tempnam('/tmp', 'tiger');
		unlink($sTempDir);
		mkdir($sTempDir);

		foreach(glob($aCMDResult['parse-tiger'].'/??_*', GLOB_ONLYDIR) as $sStateFolder)
		{
			foreach(glob($sStateFolder.'/?????_*', GLOB_ONLYDIR) as $sCountyFolder)
			{
				preg_match('#([0-9]{5})_(.*)#',basename($sCountyFolder), $aMatch);
				$sCountyID = $aMatch[1];
				$sCountyName = str_replace('_', ' ', $aMatch[2]);
				$sImportFile = $sCountyFolder.'/tl_2009_'.$sCountyID.'_edges.zip';
				if (!file_exists($sImportFile))
				{
					echo "Missing: $sImportFile\n";
				}
				$sUnzipCmd = "unzip -d $sTempDir $sImportFile";
var_dump($sUnzipCmd);
exit;
//				exec($sUnzipCmd);
			}
		}
	}

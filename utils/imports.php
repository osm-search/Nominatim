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
		foreach(glob($aCMDResult['parse-tiger'].'/??_*', GLOB_ONLYDIR) as $sStateFolder)
		{
			preg_match('#([0-9]{2})_(.*)#',basename($sStateFolder), $aMatch);
			var_dump($aMatch);
			exit;
			foreach(glob($sStateFolder.'/?????_*', GLOB_ONLYDIR) as $sCountyFolder)
			{
				set_time_limit(30);
				preg_match('#([0-9]{5})_(.*)#',basename($sCountyFolder), $aMatch);
				$sCountyID = $aMatch[1];
				$sCountyName = str_replace('_', ' ', $aMatch[2]);
				$sImportFile = $sCountyFolder.'/tl_2009_'.$sCountyID.'_edges.zip';
				$sCountyName = str_replace("'", "''", $sCountyName);
				$sCountyName = str_replace(" County", "", $sCountyName);
				echo "'$sCountyID' : '$sCountyName' ,\n";
			}
		}
exit;

		if (!file_exists(CONST_BasePath.'/data/tiger2009')) mkdir(CONST_BasePath.'/data/tiger2009');

		$sTempDir = tempnam('/tmp', 'tiger');
		unlink($sTempDir);
		mkdir($sTempDir);

		foreach(glob($aCMDResult['parse-tiger'].'/??_*', GLOB_ONLYDIR) as $sStateFolder)
		{
			foreach(glob($sStateFolder.'/?????_*', GLOB_ONLYDIR) as $sCountyFolder)
			{
				set_time_limit(30);
				preg_match('#([0-9]{5})_(.*)#',basename($sCountyFolder), $aMatch);
				$sCountyID = $aMatch[1];
				$sCountyName = str_replace('_', ' ', $aMatch[2]);
				$sImportFile = $sCountyFolder.'/tl_2009_'.$sCountyID.'_edges.zip';
				echo "$sCountyID, $sCountyName\n";
				if (!file_exists($sImportFile))
				{
					echo "Missing: $sImportFile\n";
				}
				$sUnzipCmd = "unzip -d $sTempDir $sImportFile";
				exec($sUnzipCmd);
				if (!file_exists($sTempDir.'/tl_2009_'.$sCountyID.'_edges.shp'))
				{
					echo "Failed unzip ($sCountyID)\n";
				}
				else
				{
					$sParseCmd = CONST_BasePath.'/utils/tigerAddressImport.py '.$sTempDir.'/tl_2009_'.$sCountyID.'_edges.shp';
					exec($sParseCmd);
					if (!file_exists($sTempDir.'/tl_2009_'.$sCountyID.'_edges.osm1.osm'))
					{
						echo "Failed parse ($sCountyID)\n";
					}
					else
					{
						copy($sTempDir.'/tl_2009_'.$sCountyID.'_edges.osm1.osm', CONST_BasePath.'/data/tiger2009/'.$sCountyID.'.sql');
					}
				}
				// Cleanup
				foreach(glob($sTempDir.'/*') as $sTmpFile)
				{
					unlink($sTmpFile);
				}
			}
		}
	}

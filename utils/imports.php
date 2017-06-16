#!/usr/bin/php -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');

$aCMDOptions
 = array(
    "Create and setup nominatim search system",
    array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
    array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
    array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

    array('parse-tiger', '', 0, 1, 1, 1, 'realpath', 'Convert Tiger edge files to nominatim sql import - datafiles from 2011 or later (source: edges directory of tiger data)'),
    array('patch-tiger', '', 0, 1, 0, 0, 'bool', 'Fix converted Tiger data files')
   );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);


if (isset($aCMDResult['parse-tiger'])) {
    if (!file_exists(CONST_Tiger_Data_Path)) mkdir(CONST_Tiger_Data_Path);

    $sTempDir = tempnam(sys_get_temp_dir(), 'tiger');
    unlink($sTempDir);
    mkdir($sTempDir);

    foreach (glob($aCMDResult['parse-tiger'].'/tl_20??_?????_edges.zip', 0) as $sImportFile) {
        set_time_limit(30);
        preg_match('#([0-9]{5})_(.*)#', basename($sImportFile), $aMatch);
        $sCountyID = $aMatch[1];
        echo "Processing ".$sCountyID."...\n";
        $sUnzipCmd = "unzip -d $sTempDir $sImportFile";
        exec($sUnzipCmd);
        $sShapeFile = $sTempDir.'/'.basename($sImportFile, '.zip').'.shp';
        if (!file_exists($sShapeFile)) {
            echo "Failed unzip ($sImportFile)\n";
        } else {
            $sParseCmd = CONST_BasePath.'/utils/tigerAddressImport.py '.$sShapeFile;
            exec($sParseCmd);
            $sOsmFile = $sTempDir.'/'.basename($sImportFile, '.zip').'.osm1.osm';
            if (!file_exists($sOsmFile)) {
                echo "Failed parse ($sImportFile)\n";
            } else {
                copy($sOsmFile, CONST_Tiger_Data_Path.'/'.$sCountyID.'.sql');
            }
        }
        // Cleanup
        array_map('unlink', glob($sTempDir.'/*'));
    }
}

if (isset($aCMDResult['patch-tiger'])) {
    $sPatchSQL = CONST_InstallPath.'/utils/tigerPatchSQL.sh ' . CONST_Tiger_Data_Path;
    exec($sPatchSQL);
}

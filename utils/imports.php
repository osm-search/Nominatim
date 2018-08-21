#!@PHP_BIN@ -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');

$aCMDOptions
 = array(
    'Create and setup nominatim search system',
    array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
    array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
    array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

    array('parse-tiger', '', 0, 1, 1, 1, 'realpath', 'Convert tiger edge files to nominatim sql import - datafiles from 2011 or later (source: edges directory of tiger data)'),
   );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);


if (isset($aCMDResult['parse-tiger'])) {
    if (!file_exists(CONST_Tiger_Data_Path)) mkdir(CONST_Tiger_Data_Path);

    $sTempDir = tempnam('/tmp', 'tiger');
    unlink($sTempDir);
    mkdir($sTempDir);

    foreach (glob($aCMDResult['parse-tiger'].'/tl_20??_?????_edges.zip', 0) as $sImportFile) {
        set_time_limit(30);
        preg_match('#([0-9]{5})_(.*)#', basename($sImportFile), $aMatch);
        $sCountyID = $aMatch[1];

        echo 'Processing '.$sCountyID."...\n";
        $sUnzipCmd = "unzip -d $sTempDir $sImportFile";
        exec($sUnzipCmd);

        $sShapeFilename = $sTempDir.'/'.basename($sImportFile, '.zip').'.shp';
        $sSqlFilenameTmp = $sTempDir.'/'.$sCountyID.'.sql';
        $sSqlFilename = CONST_Tiger_Data_Path.'/'.$sCountyID.'.sql';

        if (!file_exists($sShapeFilename)) {
            echo "Failed unzip ($sImportFile)\n";
        } else {
            $sParseCmd = CONST_BasePath.'/utils/tigerAddressImport.py '.$sShapeFilename.' '.$sSqlFilenameTmp;
            exec($sParseCmd);
            if (!file_exists($sSqlFilenameTmp)) {
                echo "Failed parse ($sImportFile)\n";
            } else {
                copy($sSqlFilenameTmp, $sSqlFilename);
            }
        }
        // Cleanup
        foreach (glob($sTempDir.'/*') as $sTmpFile) {
            unlink($sTmpFile);
        }
    }
}

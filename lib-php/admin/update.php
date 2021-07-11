<?php
@define('CONST_LibDir', dirname(dirname(__FILE__)));

require_once(CONST_LibDir.'/init-cmd.php');
require_once(CONST_LibDir.'/setup_functions.php');

ini_set('memory_limit', '800M');

// (long-opt, short-opt, min-occurs, max-occurs, num-arguments, num-arguments, type, help)
$aCMDOptions
= array(
   'Import / update / index osm data',
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

   array('calculate-postcodes', '', 0, 1, 0, 0, 'bool', 'Update postcode centroid table'),

   array('import-file', '', 0, 1, 1, 1, 'realpath', 'Re-import data from an OSM file'),
   array('import-diff', '', 0, 1, 1, 1, 'realpath', 'Import a diff (osc) file from local file system'),
   array('osm2pgsql-cache', '', 0, 1, 1, 1, 'int', 'Cache size used by osm2pgsql'),

   array('import-node', '', 0, 1, 1, 1, 'int', 'Re-import node'),
   array('import-way', '', 0, 1, 1, 1, 'int', 'Re-import way'),
   array('import-relation', '', 0, 1, 1, 1, 'int', 'Re-import relation'),
   array('import-from-main-api', '', 0, 1, 0, 0, 'bool', 'Use OSM API instead of Overpass to download objects'),

   array('project-dir', '', 0, 1, 1, 1, 'realpath', 'Base directory of the Nominatim installation (default: .)'),
  );

getCmdOpt($_SERVER['argv'], $aCMDOptions, $aResult, true, true);

loadSettings($aCMDResult['project-dir'] ?? getcwd());
setupHTTPProxy();

date_default_timezone_set('Etc/UTC');

$oDB = new Nominatim\DB();
$oDB->connect();
$fPostgresVersion = $oDB->getPostgresVersion();

$aDSNInfo = Nominatim\DB::parseDSN(getSetting('DATABASE_DSN'));
if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) {
    $aDSNInfo['port'] = 5432;
}

// cache memory to be used by osm2pgsql, should not be more than the available memory
$iCacheMemory = (isset($aResult['osm2pgsql-cache'])?$aResult['osm2pgsql-cache']:2000);
if ($iCacheMemory + 500 > getTotalMemoryMB()) {
    $iCacheMemory = getCacheMemoryMB();
    echo "WARNING: resetting cache memory to $iCacheMemory\n";
}

$oOsm2pgsqlCmd = (new \Nominatim\Shell(getOsm2pgsqlBinary()))
                 ->addParams('--hstore')
                 ->addParams('--latlong')
                 ->addParams('--append')
                 ->addParams('--slim')
                 ->addParams('--with-forward-dependencies', 'false')
                 ->addParams('--log-progress', 'true')
                 ->addParams('--number-processes', 1)
                 ->addParams('--cache', $iCacheMemory)
                 ->addParams('--output', 'gazetteer')
                 ->addParams('--style', getImportStyle())
                 ->addParams('--database', $aDSNInfo['database'])
                 ->addParams('--port', $aDSNInfo['port']);

if (isset($aDSNInfo['hostspec']) && $aDSNInfo['hostspec']) {
    $oOsm2pgsqlCmd->addParams('--host', $aDSNInfo['hostspec']);
}
if (isset($aDSNInfo['username']) && $aDSNInfo['username']) {
    $oOsm2pgsqlCmd->addParams('--user', $aDSNInfo['username']);
}
if (isset($aDSNInfo['password']) && $aDSNInfo['password']) {
    $oOsm2pgsqlCmd->addEnvPair('PGPASSWORD', $aDSNInfo['password']);
}
if (getSetting('FLATNODE_FILE')) {
    $oOsm2pgsqlCmd->addParams('--flat-nodes', getSetting('FLATNODE_FILE'));
}
if ($fPostgresVersion >= 11.0) {
    $oOsm2pgsqlCmd->addEnvPair(
        'PGOPTIONS',
        '-c jit=off -c max_parallel_workers_per_gather=0'
    );
}

if (isset($aResult['import-diff']) || isset($aResult['import-file'])) {
    // import diffs and files directly (e.g. from osmosis --rri)
    $sNextFile = isset($aResult['import-diff']) ? $aResult['import-diff'] : $aResult['import-file'];

    if (!file_exists($sNextFile)) {
        fail("Cannot open $sNextFile\n");
    }

    // Import the file
    $oCMD = (clone $oOsm2pgsqlCmd)->addParams($sNextFile);
    echo $oCMD->escapedCmd()."\n";
    $iRet = $oCMD->run();

    if ($iRet) {
        fail("Error from osm2pgsql, $iRet\n");
    }

    // Don't update the import status - we don't know what this file contains
}

$sTemporaryFile = CONST_InstallDir.'/osmosischange.osc';
$bHaveDiff = false;
$bUseOSMApi = isset($aResult['import-from-main-api']) && $aResult['import-from-main-api'];
$sContentURL = '';
if (isset($aResult['import-node']) && $aResult['import-node']) {
    if ($bUseOSMApi) {
        $sContentURL = 'https://www.openstreetmap.org/api/0.6/node/'.$aResult['import-node'];
    } else {
        $sContentURL = 'https://overpass-api.de/api/interpreter?data=node('.$aResult['import-node'].');out%20meta;';
    }
}

if (isset($aResult['import-way']) && $aResult['import-way']) {
    if ($bUseOSMApi) {
        $sContentURL = 'https://www.openstreetmap.org/api/0.6/way/'.$aResult['import-way'].'/full';
    } else {
        $sContentURL = 'https://overpass-api.de/api/interpreter?data=(way('.$aResult['import-way'].');%3E;);out%20meta;';
    }
}

if (isset($aResult['import-relation']) && $aResult['import-relation']) {
    if ($bUseOSMApi) {
        $sContentURL = 'https://www.openstreetmap.org/api/0.6/relation/'.$aResult['import-relation'].'/full';
    } else {
        $sContentURL = 'https://overpass-api.de/api/interpreter?data=(rel(id:'.$aResult['import-relation'].');%3E;);out%20meta;';
    }
}

if ($sContentURL) {
    file_put_contents($sTemporaryFile, file_get_contents($sContentURL));
    $bHaveDiff = true;
}

if ($bHaveDiff) {
    // import generated change file

    $oCMD = (clone $oOsm2pgsqlCmd)->addParams($sTemporaryFile);
    echo $oCMD->escapedCmd()."\n";

    $iRet = $oCMD->run();
    if ($iRet) {
        fail("osm2pgsql exited with error level $iRet\n");
    }
}

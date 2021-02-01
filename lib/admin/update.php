<?php
@define('CONST_LibDir', dirname(dirname(__FILE__)));

require_once(CONST_LibDir.'/init-cmd.php');
require_once(CONST_LibDir.'/setup_functions.php');
require_once(CONST_LibDir.'/setup/SetupClass.php');

ini_set('memory_limit', '800M');

use Nominatim\Setup\SetupFunctions as SetupFunctions;

// (long-opt, short-opt, min-occurs, max-occurs, num-arguments, num-arguments, type, help)
$aCMDOptions
= array(
   'Import / update / index osm data',
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

   array('init-updates', '', 0, 1, 0, 0, 'bool', 'Set up database for updating'),
   array('check-for-updates', '', 0, 1, 0, 0, 'bool', 'Check if new updates are available'),
   array('no-update-functions', '', 0, 1, 0, 0, 'bool', 'Do not update trigger functions to support differential updates (assuming the diff update logic is already present)'),
   array('import-osmosis', '', 0, 1, 0, 0, 'bool', 'Import updates once'),
   array('import-osmosis-all', '', 0, 1, 0, 0, 'bool', 'Import updates forever'),
   array('no-index', '', 0, 1, 0, 0, 'bool', 'Do not index the new data'),

   array('calculate-postcodes', '', 0, 1, 0, 0, 'bool', 'Update postcode centroid table'),

   array('import-file', '', 0, 1, 1, 1, 'realpath', 'Re-import data from an OSM file'),
   array('import-diff', '', 0, 1, 1, 1, 'realpath', 'Import a diff (osc) file from local file system'),
   array('osm2pgsql-cache', '', 0, 1, 1, 1, 'int', 'Cache size used by osm2pgsql'),

   array('import-node', '', 0, 1, 1, 1, 'int', 'Re-import node'),
   array('import-way', '', 0, 1, 1, 1, 'int', 'Re-import way'),
   array('import-relation', '', 0, 1, 1, 1, 'int', 'Re-import relation'),
   array('import-from-main-api', '', 0, 1, 0, 0, 'bool', 'Use OSM API instead of Overpass to download objects'),

   array('index', '', 0, 1, 0, 0, 'bool', 'Index'),
   array('index-rank', '', 0, 1, 1, 1, 'int', 'Rank to start indexing from'),
   array('index-instances', '', 0, 1, 1, 1, 'int', 'Number of indexing instances (threads)'),

   array('recompute-word-counts', '', 0, 1, 0, 0, 'bool', 'Compute frequency of full-word search terms'),
   array('update-address-levels', '', 0, 1, 0, 0, 'bool', 'Reimport address level configuration (EXPERT)'),
   array('recompute-importance', '', 0, 1, 0, 0, 'bool', 'Recompute place importances'),

   array('project-dir', '', 0, 1, 1, 1, 'realpath', 'Base directory of the Nominatim installation (default: .)'),
  );

getCmdOpt($_SERVER['argv'], $aCMDOptions, $aResult, true, true);

loadSettings($aCMDResult['project-dir'] ?? getcwd());
setupHTTPProxy();

if (!isset($aResult['index-instances'])) $aResult['index-instances'] = 1;
if (!isset($aResult['index-rank'])) $aResult['index-rank'] = 0;

date_default_timezone_set('Etc/UTC');

$oDB = new Nominatim\DB();
$oDB->connect();
$fPostgresVersion = $oDB->getPostgresVersion();

$aDSNInfo = Nominatim\DB::parseDSN(getSetting('DATABASE_DSN'));
if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;

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

$oNominatimCmd = new \Nominatim\Shell(getSetting('NOMINATIM_TOOL'));
if ($aResult['quiet']) {
    $oNominatimCmd->addParams('--quiet');
}
if ($aResult['verbose']) {
    $oNominatimCmd->addParams('--verbose');
}


if ($aResult['init-updates']) {
    $oCmd = (clone($oNominatimCmd))->addParams('replication', '--init');

    if ($aResult['no-update-functions']) {
        $oCmd->addParams('--no-update-functions');
    }

    $oCmd->run();
}

if ($aResult['check-for-updates']) {
    exit((clone($oNominatimCmd))->addParams('replication', '--check-for-updates')->run());
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

if ($aResult['calculate-postcodes']) {
    (clone($oNominatimCmd))->addParams('refresh', '--postcodes')->run();
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

if ($aResult['recompute-word-counts']) {
    (clone($oNominatimCmd))->addParams('refresh', '--word-counts')->run();
}

if ($aResult['index']) {
    (clone $oNominatimCmd)
        ->addParams('index', '--minrank', $aResult['index-rank'])
        ->addParams('--threads', $aResult['index-instances'])
        ->run();
}

if ($aResult['update-address-levels']) {
    (clone($oNominatimCmd))->addParams('refresh', '--address-levels')->run();
}

if ($aResult['recompute-importance']) {
    echo "Updating importance values for database.\n";
    $oDB = new Nominatim\DB();
    $oDB->connect();

    $sSQL = 'ALTER TABLE placex DISABLE TRIGGER ALL;';
    $sSQL .= 'UPDATE placex SET (wikipedia, importance) =';
    $sSQL .= '   (SELECT wikipedia, importance';
    $sSQL .= '    FROM compute_importance(extratags, country_code, osm_type, osm_id));';
    $sSQL .= 'UPDATE placex s SET wikipedia = d.wikipedia, importance = d.importance';
    $sSQL .= ' FROM placex d';
    $sSQL .= ' WHERE s.place_id = d.linked_place_id and d.wikipedia is not null';
    $sSQL .= '       and (s.wikipedia is null or s.importance < d.importance);';
    $sSQL .= 'ALTER TABLE placex ENABLE TRIGGER ALL;';
    $oDB->exec($sSQL);
}

if ($aResult['import-osmosis'] || $aResult['import-osmosis-all']) {
    $oCmd = (clone($oNominatimCmd))
              ->addParams('replication')
              ->addParams('--threads', $aResult['index-instances']);

    if (!$aResult['import-osmosis-all']) {
        $oCmd->addParams('--once');
    }

    if ($aResult['no-index']) {
        $oCmd->addParams('--no-index');
    }

    exit($oCmd->run());
}

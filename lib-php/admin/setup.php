<?php
@define('CONST_LibDir', dirname(dirname(__FILE__)));

require_once(CONST_LibDir.'/init-cmd.php');
require_once(CONST_LibDir.'/setup/SetupClass.php');
require_once(CONST_LibDir.'/setup_functions.php');
ini_set('memory_limit', '800M');

use Nominatim\Setup\SetupFunctions as SetupFunctions;

// (long-opt, short-opt, min-occurs, max-occurs, num-arguments, num-arguments, type, help)
$aCMDOptions
= array(
   'Create and setup nominatim search system',
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

   array('osm-file', '', 0, 1, 1, 1, 'realpath', 'File to import'),
   array('threads', '', 0, 1, 1, 1, 'int', 'Number of threads (where possible)'),

   array('all', '', 0, 1, 0, 0, 'bool', 'Do the complete process'),

   array('create-db', '', 0, 1, 0, 0, 'bool', 'Create nominatim db'),
   array('setup-db', '', 0, 1, 0, 0, 'bool', 'Build a blank nominatim db'),
   array('import-data', '', 0, 1, 0, 0, 'bool', 'Import a osm file'),
   array('osm2pgsql-cache', '', 0, 1, 1, 1, 'int', 'Cache size used by osm2pgsql'),
   array('reverse-only', '', 0, 1, 0, 0, 'bool', 'Do not create search tables and indexes'),
   array('create-functions', '', 0, 1, 0, 0, 'bool', 'Create functions'),
   array('enable-diff-updates', '', 0, 1, 0, 0, 'bool', 'Turn on the code required to make diff updates work'),
   array('enable-debug-statements', '', 0, 1, 0, 0, 'bool', 'Include debug warning statements in pgsql commands'),
   array('ignore-errors', '', 0, 1, 0, 0, 'bool', 'Continue import even when errors in SQL are present (EXPERT)'),
   array('create-tables', '', 0, 1, 0, 0, 'bool', 'Create main tables'),
   array('create-partition-tables', '', 0, 1, 0, 0, 'bool', 'Create required partition tables'),
   array('create-partition-functions', '', 0, 1, 0, 0, 'bool', 'Create required partition triggers'),
   array('no-partitions', '', 0, 1, 0, 0, 'bool', 'Do not partition search indices (speeds up import of single country extracts)'),
   array('import-wikipedia-articles', '', 0, 1, 0, 0, 'bool', 'Import wikipedia article dump'),
   array('load-data', '', 0, 1, 0, 0, 'bool', 'Copy data to live tables from import table'),
   array('disable-token-precalc', '', 0, 1, 0, 0, 'bool', 'Disable name precalculation (EXPERT)'),
   array('import-tiger-data', '', 0, 1, 0, 0, 'bool', 'Import tiger data (not included in \'all\')'),
   array('calculate-postcodes', '', 0, 1, 0, 0, 'bool', 'Calculate postcode centroids'),
   array('index', '', 0, 1, 0, 0, 'bool', 'Index the data'),
   array('index-noanalyse', '', 0, 1, 0, 0, 'bool', 'Do not perform analyse operations during index (EXPERT)'),
   array('create-search-indices', '', 0, 1, 0, 0, 'bool', 'Create additional indices required for search and update'),
   array('create-country-names', '', 0, 1, 0, 0, 'bool', 'Create default list of searchable country names'),
   array('drop', '', 0, 1, 0, 0, 'bool', 'Drop tables needed for updates, making the database readonly (EXPERIMENTAL)'),
   array('setup-website', '', 0, 1, 0, 0, 'bool', 'Used to compile environment variables for the website'),
   array('project-dir', '', 0, 1, 1, 1, 'realpath', 'Base directory of the Nominatim installation (default: .)'),
  );

// $aCMDOptions passed to getCmdOpt by reference
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

loadSettings($aCMDResult['project-dir'] ?? getcwd());
setupHTTPProxy();

$bDidSomething = false;

$oNominatimCmd = new \Nominatim\Shell(getSetting('NOMINATIM_TOOL'));
if (isset($aCMDResult['quiet']) && $aCMDResult['quiet']) {
    $oNominatimCmd->addParams('--quiet');
}
if ($aCMDResult['verbose']) {
    $oNominatimCmd->addParams('--verbose');
}

// by default, use all but one processor, but never more than 15.
$iInstances = max(1, $aCMDResult['threads'] ?? (min(16, getProcessorCount()) - 1));

function run($oCmd) {
    global $iInstances;
    $oCmd->addParams('--threads', $iInstances);
    $oCmd->run(true);
}


//*******************************************************
// Making some sanity check:
// Check if osm-file is set and points to a valid file
if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    // to remain in /lib/setup_functions.php function
    checkInFile($aCMDResult['osm-file']);
}

// ******************************************************
// instantiate Setup class
$oSetup = new SetupFunctions($aCMDResult);

// *******************************************************
// go through complete process if 'all' is selected or start selected functions
if ($aCMDResult['create-db'] || $aCMDResult['all']) {
    $bDidSomething = true;
    run((clone($oNominatimCmd))->addParams('transition', '--create-db'));
}

if ($aCMDResult['setup-db'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oCmd = (clone($oNominatimCmd))->addParams('transition', '--setup-db');

    if ($aCMDResult['no-partitions'] ?? false) {
        $oCmd->addParams('--no-partitions');
    }

    run($oCmd);
}

if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oCmd = (clone($oNominatimCmd))
        ->addParams('transition', '--import-data')
        ->addParams('--osm-file', $aCMDResult['osm-file']);
    if ($aCMDResult['drop'] ?? false) {
        $oCmd->addParams('--drop');
    }

    run($oCmd);
}

if ($aCMDResult['create-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createFunctions();
}

if ($aCMDResult['create-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createTables($aCMDResult['reverse-only']);
    $oSetup->createFunctions();
    $oSetup->createTableTriggers();
}

if ($aCMDResult['create-partition-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createPartitionTables();
}

if ($aCMDResult['create-partition-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createFunctions(); // also create partition functions
}

if ($aCMDResult['import-wikipedia-articles'] || $aCMDResult['all']) {
    $bDidSomething = true;
    // ignore errors!
    (clone($oNominatimCmd))->addParams('refresh', '--wiki-data')->run();
}

if ($aCMDResult['load-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    run((clone($oNominatimCmd))->addParams('transition', '--load-data'));
}

if ($aCMDResult['import-tiger-data']) {
    $bDidSomething = true;
    $sTigerPath = getSetting('TIGER_DATA_PATH', CONST_InstallDir.'/tiger');
    $oSetup->importTigerData($sTigerPath);
}

if ($aCMDResult['calculate-postcodes'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->calculatePostcodes($aCMDResult['all']);
}

if ($aCMDResult['index'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oCmd = (clone($oNominatimCmd))->addParams('transition', '--index');
    if ($aCMDResult['index-noanalyse'] ?? false) {
        $oCmd->addParams('--no-analyse');
    }

    run($oCmd);
}

if ($aCMDResult['drop']) {
    $bDidSomething = true;
    run((clone($oNominatimCmd))->addParams('freeze'));
}

if ($aCMDResult['create-search-indices'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createSearchIndices();
}

if ($aCMDResult['create-country-names'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createCountryNames($aCMDResult);
}

if ($aCMDResult['setup-website'] || $aCMDResult['all']) {
    $bDidSomething = true;
    run((clone($oNominatimCmd))->addParams('refresh', '--website'));
}

// ******************************************************
// If we did something, repeat the warnings
if (!$bDidSomething) {
    showUsage($aCMDOptions, true);
} else {
    echo "Summary of warnings:\n\n";
    repeatWarnings();
    echo "\n";
    info('Setup finished.');
}

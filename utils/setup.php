<?php

require_once(CONST_BasePath.'/lib/init-cmd.php');
require_once(CONST_BasePath.'/lib/setup/SetupClass.php');
require_once(CONST_BasePath.'/lib/setup_functions.php');
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
   array('osmosis-init', '', 0, 1, 0, 0, 'bool', 'Generate default osmosis configuration'),
   array('index', '', 0, 1, 0, 0, 'bool', 'Index the data'),
   array('index-noanalyse', '', 0, 1, 0, 0, 'bool', 'Do not perform analyse operations during index (EXPERT)'),
   array('create-search-indices', '', 0, 1, 0, 0, 'bool', 'Create additional indices required for search and update'),
   array('create-country-names', '', 0, 1, 0, 0, 'bool', 'Create default list of searchable country names'),
   array('drop', '', 0, 1, 0, 0, 'bool', 'Drop tables needed for updates, making the database readonly (EXPERIMENTAL)'),
  );

// $aCMDOptions passed to getCmdOpt by reference
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

$bDidSomething = false;

//*******************************************************
// Making some sanity check:
// Check if osm-file is set and points to a valid file
if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    // to remain in /lib/setup_functions.php function
    checkInFile($aCMDResult['osm-file']);
}

// osmosis init is no longer supported
if ($aCMDResult['osmosis-init']) {
    $bDidSomething = true;
    echo "Command 'osmosis-init' no longer available, please use utils/update.php --init-updates.\n";
}

// ******************************************************
// instantiate Setup class
$oSetup = new SetupFunctions($aCMDResult);

// *******************************************************
// go through complete process if 'all' is selected or start selected functions
if ($aCMDResult['create-db'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createDB();
}

$oSetup->connect();

if ($aCMDResult['setup-db'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->setupDB();
}

// Try accessing the C module, so we know early if something is wrong
if (!checkModulePresence()) {
    fail('error loading nominatim.so module');
}

if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->importData($aCMDResult['osm-file']);
}

if ($aCMDResult['create-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createFunctions();
}

if ($aCMDResult['create-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createTables($aCMDResult['reverse-only']);
    $oSetup->createFunctions();
}

if ($aCMDResult['create-partition-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createPartitionTables();
}

if ($aCMDResult['create-partition-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createPartitionFunctions();
}

if ($aCMDResult['import-wikipedia-articles'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->importWikipediaArticles();
}

if ($aCMDResult['load-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->loadData($aCMDResult['disable-token-precalc']);
}

if ($aCMDResult['import-tiger-data']) {
    $bDidSomething = true;
    $oSetup->importTigerData();
}

if ($aCMDResult['calculate-postcodes'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->calculatePostcodes($aCMDResult['all']);
}

if ($aCMDResult['index'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->index($aCMDResult['index-noanalyse']);
}

if ($aCMDResult['create-search-indices'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createSearchIndices();
}

if ($aCMDResult['create-country-names'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $oSetup->createCountryNames($aCMDResult);
}

if ($aCMDResult['drop']) {
    $bDidSomething = true;
    $oSetup->drop($aCMDResult);
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

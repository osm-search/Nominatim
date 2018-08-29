#!@PHP_BIN@ -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
include_once(CONST_InstallPath.'/utils/setupClass.php');
// ->indirect via init-cmd.php -> /lib/cmd.php                  for runWithEnv, getCmdOpt
// ->indirect via init-cmd.php -> /lib/init.php -> db.php       for &getDB()

include_once(CONST_BasePath.'/lib/setup_functions.php');
include_once(CONST_BasePath.'/lib/setup_functions.php');
ini_set('memory_limit', '800M');


$aCMDOptions = createSetupArgvArray();

// $aCMDOptions passed to getCmdOpt by reference
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);


$bDidSomething = false;

//*******************************************************
// Making some sanity check:
// Check if osm-file is set and points to a valid file
if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    // to remain in /lib/setup_functions.php function
    checkInFile($aCMDResult['osm-file']);
    echo $aCMDResult['osm-file'];
}

// osmosis init is no longer supported
if ($aCMDResult['osmosis-init']) {
    $bDidSomething = true;
    echo "Command 'osmosis-init' no longer available, please use utils/update.php --init-updates.\n";
}

// ******************************************************
// instantiate Setup class
$cSetup = new SetupFunctions($aCMDResult);
if ($aCMDResult['create-db'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> createDB();
}

// *******************************************************
// go through complete process if 'all' is selected or start selected functions
if ($aCMDResult['setup-db'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> setupDB();
}

// Try accessing the C module, so we know early if something is wrong
if (!checkModulePresence()) {
    fail('error loading nominatim.so module');
}

if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> importData($aCMDResult['osm-file']);
}
 
if ($aCMDResult['create-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> createFunctions();
}

if ($aCMDResult['create-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> createTables();
    $cSetup -> recreateFunction();
}

if ($aCMDResult['create-partition-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> createPartitionTables();
}

if ($aCMDResult['create-partition-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> createPartitionFunctions();
}

if ($aCMDResult['import-wikipedia-articles'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> importWikipediaArticles();
}

if ($aCMDResult['load-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> loadData($aCMDResult['disable-token-precalc']);
}
    
if ($aCMDResult['import-tiger-data']) {
    $bDidSomething = true;
    $cSetup -> importTigerData();
}

if ($aCMDResult['calculate-postcodes'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> calculatePostcodes($aCMDResult['all']);
}

if ($aCMDResult['index'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> index($aCMDResult['index-noanalyse']);
}

if ($aCMDResult['create-search-indices'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> createSearchIndices();
}

if ($aCMDResult['create-country-names'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $cSetup -> createCountryNames($aCMDResult);
}

if ($aCMDResult['drop']) {
    $bDidSomething = true;
    $cSetup -> drop($aCMDResult);
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

#!@PHP_BIN@ -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
include_once(CONST_BasePath.'/lib/setup_functions.php');
ini_set('memory_limit', '800M');

# (long-opt, short-opt, min-occurs, max-occurs, num-arguments, num-arguments, type, help)

$aCMDOptions = createSetupArgvArray();

getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

$bDidSomething = false;

// Check if osm-file is set and points to a valid file if --all or --import-data is given
checkInFile($aCMDResult);

// get info how many processors and huch much cache mem we can use
$prepSreturn = prepSystem($aCMDResult);
$iCacheMemory = $prepSreturn[0];
$iInstances = $prepSreturn[1];

// prepares DB for import or update, returns Data Source Name
$aDSNInfo = prepDB($aCMDResult);

if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    importData($aCMDResult, $iCacheMemory, $aDSNInfo);
}

if ($aCMDResult['create-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    createFunctions($aCMDResult);
}

if ($aCMDResult['create-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    createTables($aCMDResult);
}

if ($aCMDResult['create-partition-tables'] || $aCMDResult['all']) {
    $bDidSomething = true;
    createPartitionTables($aCMDResult);
}

if ($aCMDResult['create-partition-functions'] || $aCMDResult['all']) {
    $bDidSomething = true;
    createPartitionFunctions($aCMDResult);
}

if ($aCMDResult['import-wikipedia-articles'] || $aCMDResult['all']) {
    $bDidSomething = true;
    importWikipediaArticles();
}


if ($aCMDResult['load-data'] || $aCMDResult['all']) {
    $bDidSomething = true;
    loadData($aCMDResult, $iInstances);
}

if ($aCMDResult['import-tiger-data']) {
    $bDidSomething = true;
    importTigerData($aCMDResult, $iInstances);
}

if ($aCMDResult['calculate-postcodes'] || $aCMDResult['all']) {
    $bDidSomething = true;
    calculatePostcodes($aCMDResult);
}

if ($aCMDResult['osmosis-init']) {
    $bDidSomething = true;
    echo "Command 'osmosis-init' no longer available, please use utils/update.php --init-updates.\n";
}

if ($aCMDResult['index'] || $aCMDResult['all']) {
    $bDidSomething = true;
    index($aCMDResult, $aDSNInfo, $iInstances);
}

if ($aCMDResult['create-search-indices'] || $aCMDResult['all']) {
    $bDidSomething = true;
    createSearchIndices($aCMDResult);
}

if ($aCMDResult['create-country-names'] || $aCMDResult['all']) {
    $bDidSomething = true;
    createCountryNames($aCMDResult);
}

if ($aCMDResult['drop']) {
    $bDidSomething = true;
    drop($aCMDResult);
}

didSomething($bDidSomething);

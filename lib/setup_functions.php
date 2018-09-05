<?php

function checkInFile($sOSMFile)
{
    if (!isset($sOSMFile)) {
        fail('missing --osm-file for data import');
    }

    if (!file_exists($sOSMFile)) {
        fail('the path supplied to --osm-file does not exist');
    }

    if (!is_readable($sOSMFile)) {
        fail('osm-file "' . $aCMDResult['osm-file'] . '" not readable');
    }
}

function checkModulePresence()
{
    // Try accessing the C module, so we know early if something is wrong
    // and can simply error out.
    $sModulePath = CONST_Database_Module_Path;
    $sSQL = "CREATE FUNCTION nominatim_test_import_func(text) RETURNS text AS '";
    $sSQL .= $sModulePath . "/nominatim.so', 'transliteration' LANGUAGE c IMMUTABLE STRICT";
    $sSQL .= ';DROP FUNCTION nominatim_test_import_func(text);';

    $oDB = &getDB();
    $oResult = $oDB->query($sSQL);

    $bResult = true;

    if (PEAR::isError($oResult)) {
        echo "\nERROR: Failed to load nominatim module. Reason:\n";
        echo $oResult->userinfo . "\n\n";
        $bResult = false;
    }

    return $bResult;
}

// (long-opt, short-opt, min-occurs, max-occurs, num-arguments, num-arguments, type, help)
// create and array
function createSetupArgvArray()
{
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
    return $aCMDOptions;
}

function createUpdateArgvArray()
{
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

        array('deduplicate', '', 0, 1, 0, 0, 'bool', 'Deduplicate tokens'),
        array('recompute-word-counts', '', 0, 1, 0, 0, 'bool', 'Compute frequency of full-word search terms'),
        array('no-npi', '', 0, 1, 0, 0, 'bool', '(obsolete)'),

        array('create-functions', '', 0, 1, 1, 1, 'bool', 'Create functions'),
        array('enable-diff-updates', '', 0, 1, 1, 1, 'bool', 'Turn on the code required to make diff updates work'),
    );
    return $aCMDOptions;
}

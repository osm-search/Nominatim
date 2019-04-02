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
    // Try accessing the C module, so we know early if something is wrong.
    // Raises Nominatim\DatabaseError on failure

    $sModulePath = CONST_Database_Module_Path;
    $sSQL = "CREATE FUNCTION nominatim_test_import_func(text) RETURNS text AS '";
    $sSQL .= $sModulePath . "/nominatim.so', 'transliteration' LANGUAGE c IMMUTABLE STRICT";
    $sSQL .= ';DROP FUNCTION nominatim_test_import_func(text);';

    $oDB = new \Nominatim\DB();
    $oDB->connect();
    $oDB->exec($sSQL, null, 'Database server failed to load '.$sModulePath.'/nominatim.so module');
}

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

function getOsm2pgsqlBinary()
{
    return getSetting('OSM2PGSQL_BINARY', CONST_Default_Osm2pgsql);
}

function getImportStyle()
{
    $sStyle = getSetting('IMPORT_STYLE');

    if (in_array($sStyle, array('admin', 'street', 'address', 'full', 'extratags'))) {
        return CONST_DataDir.'/settings/import-'.$sStyle.'.style';
    }

    return $sStyle;
}

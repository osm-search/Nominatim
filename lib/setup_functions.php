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
    $sBinary = getSetting('OSM2PGSQL_BINARY');
    if (!$sBinary) {
        $sBinary = CONST_InstallDir.'/osm2pgsql/osm2pgsql';
    }

    return $sBinary;
}

function getImportStyle()
{
    $sStyle = getSetting('IMPORT_STYLE');

    if (in_array($sStyle, array('admin', 'street', 'address', 'full', 'extratags'))) {
        return CONST_DataDir.'/settings/import-'.$sStyle.'.style';
    }

    return $sStyle;
}

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

<?php


function formatOSMType($sType, $bIncludeExternal = true)
{
    if ($sType == 'N') {
        return 'node';
    }
    if ($sType == 'W') {
        return 'way';
    }
    if ($sType == 'R') {
        return 'relation';
    }

    if (!$bIncludeExternal) {
        return '';
    }

    if ($sType == 'T') {
        return 'way';
    }
    if ($sType == 'I') {
        return 'way';
    }

    // not handled: P, L

    return '';
}

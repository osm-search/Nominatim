<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */


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

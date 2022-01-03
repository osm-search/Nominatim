<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

function getOsm2pgsqlBinary()
{
    $sBinary = getSetting('OSM2PGSQL_BINARY');

    return $sBinary ? $sBinary : CONST_Default_Osm2pgsql;
}

function getImportStyle()
{
    $sStyle = getSetting('IMPORT_STYLE');

    if (in_array($sStyle, array('admin', 'street', 'address', 'full', 'extratags'))) {
        return CONST_ConfigDir.'/import-'.$sStyle.'.style';
    }

    return $sStyle;
}

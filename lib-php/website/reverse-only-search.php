<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

require_once(CONST_LibDir.'/init-website.php');
require_once(CONST_LibDir.'/ParameterParser.php');

$oParams = new Nominatim\ParameterParser();

// Format for output
$sOutputFormat = $oParams->getSet('format', array('xml', 'json', 'jsonv2', 'geojson', 'geocodejson'), 'jsonv2');
set_exception_handler_by_format($sOutputFormat);

throw new Exception('Reverse-only import does not support forward searching.', 404);

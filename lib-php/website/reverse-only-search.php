<?php

require_once(CONST_LibDir.'/init-website.php');
require_once(CONST_LibDir.'/ParameterParser.php');

$oParams = new Nominatim\ParameterParser();

// Format for output
$sOutputFormat = $oParams->getSet('format', array('xml', 'json', 'jsonv2', 'geojson', 'geocodejson'), 'jsonv2');
set_exception_handler_by_format($sOutputFormat);

throw new Exception('Reverse-only import does not support forward searching.', 404);

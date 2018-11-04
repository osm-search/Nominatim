#!/usr/bin/php
<?php

include('vendor/autoload.php');

use proj4php\Proj4php;
use proj4php\Proj;
use proj4php\Point;

$oProj4 = new Proj4php();
$oProjOSGB36 = new Proj('EPSG:27700', $oProj4);
$oProjWGS84  = new Proj('EPSG:4326', $oProj4);

echo <<< EOT

-- This data contains Ordnance Survey data © Crown copyright and database right 2010.
-- Code-Point Open contains Royal Mail data © Royal Mail copyright and database right 2010.
-- OS data may be used under the terms of the OS OpenData licence:
-- http://www.ordnancesurvey.co.uk/oswebsite/opendata/licence/docs/licence.pdf

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;

COPY gb_postcode (id, postcode, x, y) FROM stdin;

EOT;

$iCounter = 0;
while ($sLine = fgets(STDIN)) {
    $aColumns = str_getcsv($sLine);

    // https://stackoverflow.com/questions/9144592/php-split-a-postcode-into-two-parts#comment11589150_9144834
    // insert space before the third last position
    $sPostcode = $aColumns[0];
    $sPostcode = preg_replace('/\s*(...)$/', ' $1', $sPostcode);
    $iNorthings = $aColumns[2];
    $iEastings = $aColumns[3];

    $oPointWGS84 = $oProj4->transform($oProjWGS84, new Point($iNorthings, $iEastings, $oProjOSGB36));
    list($fLon, $fLat) = $oPointWGS84->toArray();

    echo join("\t", array($iCounter, $sPostcode, $fLon, $fLat))."\n";

    $iCounter = $iCounter + 1;
}

echo <<< EOT
\.
EOT;

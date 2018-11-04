#!/usr/bin/env php
<?php

echo <<< EOT

ALTER TABLE gb_postcode ADD COLUMN easting bigint;
ALTER TABLE gb_postcode ADD COLUMN northing bigint;

TRUNCATE gb_postcode;

COPY gb_postcode (id, postcode, easting, northing) FROM stdin;

EOT;

$iCounter = 0;
while ($sLine = fgets(STDIN)) {
    $aColumns = str_getcsv($sLine);

    // insert space before the third last position
    // https://stackoverflow.com/a/9144834
    $postcode = $aColumns[0];
    $postcode = preg_replace('/\s*(...)$/', ' $1', $postcode);

    echo join("\t", array($iCounter, $postcode, $aColumns[2], $aColumns[3]))."\n";

    $iCounter = $iCounter + 1;
}

echo <<< EOT
\.

UPDATE gb_postcode SET geometry=ST_Transform(ST_SetSRID(CONCAT('POINT(', easting, ' ', northing, ')')::geometry, 27700), 4326);

ALTER TABLE gb_postcode DROP COLUMN easting;
ALTER TABLE gb_postcode DROP COLUMN northing;

EOT;

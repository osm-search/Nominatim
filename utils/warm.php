<?php

require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');

$aCMDOptions = array(
                'Tools to warm nominatim db',
                array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
                array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
                array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),
                array('reverse-only', '', 0, 1, 0, 0, 'bool', 'Warm reverse only'),
                array('search-only', '', 0, 1, 0, 0, 'bool', 'Warm search only'),
               );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aResult, true, true);

require_once(CONST_BasePath.'/lib/log.php');
require_once(CONST_BasePath.'/lib/Geocode.php');
require_once(CONST_BasePath.'/lib/PlaceLookup.php');
require_once(CONST_BasePath.'/lib/ReverseGeocode.php');

$oDB =& getDB();

$bVerbose = $aResult['verbose'];

if (!$aResult['search-only']) {
    $oReverseGeocode = new Nominatim\ReverseGeocode($oDB);
    $oReverseGeocode->setZoom(20);
    $oPlaceLookup = new Nominatim\PlaceLookup($oDB);
    $oPlaceLookup->setIncludeAddressDetails(true);
    $oPlaceLookup->setLanguagePreference(array('en'));

    echo 'Warm reverse: ';
    if ($bVerbose) echo "\n";
    for ($i = 0; $i < 1000; $i++) {
        $fLat = rand(-9000, 9000) / 100;
        $fLon = rand(-18000, 18000) / 100;
        if ($bVerbose) echo "$fLat, $fLon = ";
        $oLookup = $oReverseGeocode->lookup($fLat, $fLon);
        if ($oLookup) {
            $aDetails = $oPlaceLookup->lookup(array($oLookup->iId => $oLookup));
            if ($bVerbose) echo $aDetails['langaddress']."\n";
        } else {
            echo '.';
        }
    }
    echo "\n";
}

if (!$aResult['reverse-only']) {
    $oGeocode = new Nominatim\Geocode($oDB);

    echo 'Warm search: ';
    if ($bVerbose) echo "\n";
    $sSQL = 'select word from word where word is not null order by search_name_count desc limit 1000';
    foreach ($oDB->getCol($sSQL) as $sWord) {
        if ($bVerbose) echo "$sWord = ";
        $oGeocode->setLanguagePreference(array('en'));
        $oGeocode->setQuery($sWord);
        $aSearchResults = $oGeocode->lookup();
        if ($bVerbose) echo $aSearchResults[0]['langaddress']."\n";
        else echo '.';
    }
}

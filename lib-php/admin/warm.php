<?php
@define('CONST_LibDir', dirname(dirname(__FILE__)));

require_once(CONST_LibDir.'/init-cmd.php');
require_once(CONST_LibDir.'/log.php');
require_once(CONST_LibDir.'/PlaceLookup.php');
require_once(CONST_LibDir.'/ReverseGeocode.php');

ini_set('memory_limit', '800M');

$aCMDOptions = array(
                'Tools to warm nominatim db',
                array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
                array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
                array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),
                array('reverse-only', '', 0, 1, 0, 0, 'bool', 'Warm reverse only'),
                array('search-only', '', 0, 1, 0, 0, 'bool', 'Warm search only'),
                array('project-dir', '', 0, 1, 1, 1, 'realpath', 'Base directory of the Nominatim installation (default: .)'),
               );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aResult, true, true);

loadSettings($aCMDResult['project-dir'] ?? getcwd());

@define('CONST_Database_DSN', getSetting('DATABASE_DSN'));
@define('CONST_Default_Language', getSetting('DEFAULT_LANGUAGE', false));
@define('CONST_Log_DB', getSettingBool('LOG_DB'));
@define('CONST_Log_File', getSetting('LOG_FILE', false));
@define('CONST_NoAccessControl', getSettingBool('CORS_NOACCESSCONTROL'));
@define('CONST_Places_Max_ID_count', getSetting('LOOKUP_MAX_COUNT'));
@define('CONST_PolygonOutput_MaximumTypes', getSetting('POLYGON_OUTPUT_MAX_TYPES'));
@define('CONST_Search_BatchMode', getSettingBool('SEARCH_BATCH_MODE'));
@define('CONST_Search_NameOnlySearchFrequencyThreshold', getSetting('SEARCH_NAME_ONLY_THRESHOLD'));
@define('CONST_Use_US_Tiger_Data', getSettingBool('USE_US_TIGER_DATA'));
@define('CONST_MapIcon_URL', getSetting('MAPICON_URL', false));
@define('CONST_TokenizerDir', CONST_InstallDir.'/tokenizer');

require_once(CONST_LibDir.'/Geocode.php');

$oDB = new Nominatim\DB();
$oDB->connect();

$bVerbose = $aResult['verbose'];

function print_results($aResults, $bVerbose)
{
    if ($bVerbose) {
        if ($aResults && count($aResults)) {
            echo $aResults[0]['langaddress']."\n";
        } else {
            echo "<not found>\n";
        }
    } else {
        echo '.';
    }
}

if (!$aResult['search-only']) {
    $oReverseGeocode = new Nominatim\ReverseGeocode($oDB);
    $oReverseGeocode->setZoom(20);
    $oPlaceLookup = new Nominatim\PlaceLookup($oDB);
    $oPlaceLookup->setIncludeAddressDetails(true);
    $oPlaceLookup->setLanguagePreference(array('en'));

    echo 'Warm reverse: ';
    if ($bVerbose) {
        echo "\n";
    }
    for ($i = 0; $i < 1000; $i++) {
        $fLat = rand(-9000, 9000) / 100;
        $fLon = rand(-18000, 18000) / 100;
        if ($bVerbose) {
            echo "$fLat, $fLon = ";
        }

        $oLookup = $oReverseGeocode->lookup($fLat, $fLon);
        $aSearchResults = $oLookup ? $oPlaceLookup->lookup(array($oLookup->iId => $oLookup)) : null;
        print_results($aSearchResults, $bVerbose);
    }
    echo "\n";
}

if (!$aResult['reverse-only']) {
    $oGeocode = new Nominatim\Geocode($oDB);

    echo 'Warm search: ';
    if ($bVerbose) {
        echo "\n";
    }
    $sSQL = 'SELECT word FROM word WHERE word is not null ORDER BY search_name_count DESC LIMIT 1000';
    foreach ($oDB->getCol($sSQL) as $sWord) {
        if ($bVerbose) {
            echo "$sWord = ";
        }

        $oGeocode->setLanguagePreference(array('en'));
        $oGeocode->setQuery($sWord);
        $aSearchResults = $oGeocode->lookup();
        print_results($aSearchResults, $bVerbose);
    }
    echo "\n";
}

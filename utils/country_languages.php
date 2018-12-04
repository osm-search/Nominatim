<?php

require_once(CONST_BasePath.'/lib/init-cmd.php');

ini_set('memory_limit', '800M');
ini_set('display_errors', 'stderr');

$aCMDOptions
 = array(
    'Import country language data from osm wiki',
    array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
    array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
    array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),
   );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

include(CONST_Phrase_Config);

if (true) {
    $sURL = 'https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Country_Codes';
    $sWikiPageXML = file_get_contents($sURL);
    if (preg_match_all('#\\| ([a-z]{2}) \\|\\| [^|]+\\|\\| ([a-z,]+)#', $sWikiPageXML, $aMatches, PREG_SET_ORDER)) {
        foreach ($aMatches as $aMatch) {
            $aLanguages = explode(',', $aMatch[2]);
            foreach ($aLanguages as $i => $s) {
                $aLanguages[$i] = '"'.pg_escape_string($s).'"';
            }
            echo "UPDATE country_name set country_default_language_codes = '{".join(',', $aLanguages)."}' where country_code = '".pg_escape_string($aMatch[1])."';\n";
        }
    }
}

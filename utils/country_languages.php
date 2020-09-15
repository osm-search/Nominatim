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

// https://wiki.openstreetmap.org/wiki/Nominatim/Country_Codes
$sExportURL = 'https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Country_Codes';
$sWikiPageXML = file_get_contents($sExportURL);

// |-
// |style="text-align:center"| &lt;tt&gt;WS&lt;/tt&gt; || Samoa
// | {{Lang|en|Samoa}}
// | &lt;tt title="{{Languagename|sm|en}}"&gt;sm&lt;/tt&gt;, &lt;tt title="{{Languagename|en|en}}"&gt;en&lt;/tt&gt;

$sWikiPageXML = str_replace('&lt;', '<', $sWikiPageXML);
$sWikiPageXML = str_replace('&gt;', '>', $sWikiPageXML);

// |-
// |style="text-align:center"| <tt>WS</tt> || Samoa
// | {{Lang|en|Samoa}}
// | <tt title="{{Languagename|sm|en}}">sm</tt>, <tt title="{{Languagename|en|en}}">en</tt>

$sWikiPageXML = strip_tags($sWikiPageXML);

// |-
// |style="text-align:center"| WS || Samoa
// | {{Lang|en|Samoa}}
// | sm, en

$sWikiPageXML = preg_replace('/\{\{.+\}\}/', '$1', $sWikiPageXML);

// |-
// |style="text-align:center"| WS || Samoa
// |
// | sm, en

$sWikiPageXML = preg_replace('/\n/', ' ', $sWikiPageXML);
$sWikiPageXML = preg_replace('/\|-/', "\n", $sWikiPageXML);

 // |style="text-align:center"| WS || Samoa |  | sm, en

if (!preg_match_all('#\\| ([A-Z]{2}) \\|\\| [^|]+\\| [^|]+\\| ([a-z, ]+)#', $sWikiPageXML, $aMatches, PREG_SET_ORDER)) {
    fail('Unable to parse table');
}

if (count($aMatches) < 245) {
    fail('Expected at least 245 countries');
}

foreach ($aMatches as $aMatch) {
    // 'ab, cd, ef' => ['"ab"', '"cd"', '"ef"']
    $aLanguages = array_map(function ($sLang) {
        return '"'.pg_escape_string(trim($sLang)).'"';
    }, explode(',', $aMatch[2]));

    // UPDATE country_name SET country_default_language_codes = '{"bi","en","fr"}' WHERE country_code = 'VU';
    printf(
        "UPDATE country_name SET country_default_language_codes = '{%s}' WHERE country_code = '%s';\n",
        join(',', $aLanguages),
        pg_escape_string($aMatch[1])
    );
}

exit(0);

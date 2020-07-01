<?php

require_once(CONST_BasePath.'/lib/init-cmd.php');
require_once(CONST_BasePath.'/lib/names.php');
ini_set('memory_limit', '800M');
ini_set('display_errors', 'stderr');

$aCMDOptions
= array(
   'Import and export special phrases',
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),
   array('wiki-import', '', 0, 1, 0, 0, 'bool', 'Create import script for search phrases '),
   array('languages', '', 0, 1, 0, 0, 'string', 'list of languages '),
  );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

include(CONST_Phrase_Config);

if ($aCMDResult['wiki-import']) {
    $oNormalizer = Transliterator::createFromRules(CONST_Term_Normalization_Rules);
    $aPairs = array();

    $sLanguageIn =
        $aCMDResult['languages'] ?
            $aCMDResult['languages'] :
            CONST_languages ?
                CONST_languages:
                ('af,ar,br,ca,cs,de,en,es,et,eu,fa,fi,fr,gl,hr,hu,'.
                'ia,is,it,ja,mk,nl,no,pl,ps,pt,ru,sk,sl,sv,uk,vi');

    foreach (explode(',', $sLanguageIn) as $sLanguage) {
        $sURL = 'https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/'.strtoupper($sLanguage);
        $sWikiPageXML = file_get_contents($sURL);

        if (!preg_match_all(
            '#\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([\\-YN])#',
            $sWikiPageXML,
            $aMatches,
            PREG_SET_ORDER
        )) {
            continue;
        }

        foreach ($aMatches as $aMatch) {
            $sLabel = trim($aMatch[1]);
            if ($oNormalizer !== null) {
                $sTrans = pg_escape_string($oNormalizer->transliterate($sLabel));
            } else {
                $sTrans = null;
            }
            $sClass = trim($aMatch[2]);
            $sType = trim($aMatch[3]);
            // hack around a bug where building=yes was imported with
            // quotes into the wiki
            $sType = preg_replace('/(&quot;|")/', '', $sType);
            // sanity check, in case somebody added garbage in the wiki
            if (preg_match('/^\\w+$/', $sClass) < 1
                || preg_match('/^\\w+$/', $sType) < 1
            ) {
                trigger_error("Bad class/type for language $sLanguage: $sClass=$sType");
                exit;
            }
            // blacklisting: disallow certain class/type combinations
            if (isset($aTagsBlacklist[$sClass]) && in_array($sType, $aTagsBlacklist[$sClass])) {
                // fwrite(STDERR, "Blacklisted: ".$sClass."/".$sType."\n");
                continue;
            }
            // whitelisting: if class is in whitelist, allow only tags in the list
            if (isset($aTagsWhitelist[$sClass]) && !in_array($sType, $aTagsWhitelist[$sClass])) {
                // fwrite(STDERR, "Non-Whitelisted: ".$sClass."/".$sType."\n");
                continue;
            }
            $aPairs[$sClass.'|'.$sType] = array($sClass, $sType);

            switch (trim($aMatch[4])) {
                case 'near':
                    printf(
                        "SELECT getorcreate_amenityoperator(make_standard_name('%s'), '%s', '%s', '%s', 'near');\n",
                        pg_escape_string($sLabel),
                        $sTrans,
                        $sClass,
                        $sType
                    );
                    break;
                case 'in':
                    printf(
                        "SELECT getorcreate_amenityoperator(make_standard_name('%s'), '%s', '%s', '%s', 'in');\n",
                        pg_escape_string($sLabel),
                        $sTrans,
                        $sClass,
                        $sType
                    );
                    break;
                default:
                    printf(
                        "SELECT getorcreate_amenity(make_standard_name('%s'), '%s', '%s', '%s');\n",
                        pg_escape_string($sLabel),
                        $sTrans,
                        $sClass,
                        $sType
                    );
                    break;
            }
        }
    }


    foreach ($aPairs as $aPair) {
        printf(
            'CREATE INDEX %s'
            . ' ON placex'
            . " WHERE class = '%s' AND type = '%s'"
            . ";\n",
            pg_escape_string(indexClassType($aPair[0], §$aPair[1])),
            pg_escape_string($aPair[0]),
            pg_escape_string($aPair[1])
        );
    }
}

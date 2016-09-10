#!/usr/bin/php -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');
ini_set('display_errors', 'stderr');

$aCMDOptions
= array(
   "Import and export special phrases",
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),
   array('countries', '', 0, 1, 0, 0, 'bool', 'Create import script for country codes and names'),
   array('wiki-import', '', 0, 1, 0, 0, 'bool', 'Create import script for search phrases '),
  );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

include(CONST_InstallPath.'/settings/phrase_settings.php');


if ($aCMDResult['countries']) {
    echo "select getorcreate_country(make_standard_name('uk'), 'gb');\n";
    echo "select getorcreate_country(make_standard_name('united states'), 'us');\n";
    echo "select count(*) from (select getorcreate_country(make_standard_name(country_code), country_code) from country_name where country_code is not null) as x;\n";

    echo "select count(*) from (select getorcreate_country(make_standard_name(get_name_by_language(country_name.name,ARRAY['name'])), country_code) from country_name where get_name_by_language(country_name.name, ARRAY['name']) is not null) as x;\n";
    foreach ($aLanguageIn as $sLanguage) {
        echo "select count(*) from (select getorcreate_country(make_standard_name(get_name_by_language(country_name.name,ARRAY['name:".$sLanguage."'])), country_code) from country_name where get_name_by_language(country_name.name, ARRAY['name:".$sLanguage."']) is not null) as x;\n";
    }
}

if ($aCMDResult['wiki-import']) {
    $aPairs = array();

    foreach ($aLanguageIn as $sLanguage) {
        $sURL = 'http://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/'.strtoupper($sLanguage);
        $sWikiPageXML = file_get_contents($sURL);
        if (preg_match_all('#\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([\\-YN])#', $sWikiPageXML, $aMatches, PREG_SET_ORDER)) {
            foreach ($aMatches as $aMatch) {
                $sLabel = trim($aMatch[1]);
                $sClass = trim($aMatch[2]);
                $sType = trim($aMatch[3]);
                # hack around a bug where building=yes was imported with
                # quotes into the wiki
                $sType = preg_replace('/&quot;/', '', $sType);
                # sanity check, in case somebody added garbage in the wiki
                if (preg_match('/^\\w+$/', $sClass) < 1 ||
                    preg_match('/^\\w+$/', $sType) < 1) {
                    trigger_error("Bad class/type for language $sLanguage: $sClass=$sType");
                    exit;
                }
                # blacklisting: disallow certain class/type combinations
                if (isset($aTagsBlacklist[$sClass]) && in_array($sType, $aTagsBlacklist[$sClass])) {
                    # fwrite(STDERR, "Blacklisted: ".$sClass."/".$sType."\n");
                    continue;
                }
                # whitelisting: if class is in whitelist, allow only tags in the list
                if (isset($aTagsWhitelist[$sClass]) && !in_array($sType, $aTagsWhitelist[$sClass])) {
                    # fwrite(STDERR, "Non-Whitelisted: ".$sClass."/".$sType."\n");
                    continue;
                }
                $aPairs[$sClass.'|'.$sType] = array($sClass, $sType);

                switch (trim($aMatch[4])) {
                    case 'near':
                        echo "select getorcreate_amenityoperator(make_standard_name('".pg_escape_string($sLabel)."'), '$sClass', '$sType', 'near');\n";
                        break;
                    case 'in':
                        echo "select getorcreate_amenityoperator(make_standard_name('".pg_escape_string($sLabel)."'), '$sClass', '$sType', 'in');\n";
                        break;
                    default:
                        echo "select getorcreate_amenity(make_standard_name('".pg_escape_string($sLabel)."'), '$sClass', '$sType');\n";
                        break;
                }
            }
        }
    }

    echo "create index idx_placex_classtype on placex (class, type);";

    foreach ($aPairs as $aPair) {
        echo "create table place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1]);
        if (CONST_Tablespace_Aux_Data)
            echo " tablespace ".CONST_Tablespace_Aux_Data;
        echo " as select place_id as place_id,st_centroid(geometry) as centroid from placex where ";
        echo "class = '".pg_escape_string($aPair[0])."' and type = '".pg_escape_string($aPair[1])."'";
        echo ";\n";

        echo "CREATE INDEX idx_place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])."_centroid ";
        echo "ON place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])." USING GIST (centroid)";
        if (CONST_Tablespace_Aux_Index)
            echo " tablespace ".CONST_Tablespace_Aux_Index;
        echo ";\n";

        echo "CREATE INDEX idx_place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])."_place_id ";
        echo "ON place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])." USING btree(place_id)";
        if (CONST_Tablespace_Aux_Index)
            echo " tablespace ".CONST_Tablespace_Aux_Index;
        echo ";\n";

        echo "GRANT SELECT ON place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1]).' TO "'.CONST_Database_Web_User."\";\n";
    }

    echo "drop index idx_placex_classtype;";
}

#!/usr/bin/php -Cq
<?php

        require_once(dirname(dirname(__FILE__)).'/lib/init-cmd.php');
        ini_set('memory_limit', '800M');

        $aCMDOptions = array(
                "Import and export special phrases",
                array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
                array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
                array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

                array('wiki-import', '', 0, 1, 0, 0, 'bool', 'Create nominatim db'),
        );
        getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

	$aLanguageIn = array(
			'af',
			'ar',
			'br',
			'ca',
			'cs',
			'de',
			'en',
			'es',
			'et',
			'eu',
			'fa',
			'fi',
			'fr',
			'gl',
			'hr',
			'hu',
			'ia',
			'is',
			'it',
			'ja',
			'mk',
			'nl',
			'no',
			'pl',
			'ps',
			'pt',
			'ru',
			'sk',
			'sv',
			'uk',
			'vi',
		);

	if ($aCMDResult['wiki-import'])
	{
		$aPairs = array();

		foreach($aLanguageIn as $sLanguage)
		{
			$sURL = 'http://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/'.strtoupper($sLanguage);
			$sWikiPageXML = file_get_contents($sURL);
			if (preg_match_all('#\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([^|]+) \\|\\| ([\\-YN])#', $sWikiPageXML, $aMatches, PREG_SET_ORDER))
			{
				foreach($aMatches as $aMatch)
				{
					$sLabel = $aMatch[1];
					$sClass = $aMatch[2];
					$sType = $aMatch[3];
					$aPairs[$sClass.'|'.$sType] = array($sClass, $sType);

					switch(trim($aMatch[4]))
					{
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

		foreach($aPairs as $aPair)
		{
			if ($aPair[1] == 'highway') continue;

			echo "create table place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])." as ";
			echo "select place_id as place_id,st_centroid(geometry) as centroid from placex where ";
			echo "class = '".pg_escape_string($aPair[0])."' and type = '".pg_escape_string($aPair[1])."';\n";

			echo "CREATE INDEX idx_place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])."_centroid ";
			echo "ON place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])." USING GIST (centroid);\n";

			echo "CREATE INDEX idx_place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])."_place_id ";
			echo "ON place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])." USING btree(place_id);\n";

            echo "GRANT SELECT ON place_classtype_".pg_escape_string($aPair[0])."_".pg_escape_string($aPair[1])." TO \"www-data\";";

		}

        echo "drop index idx_placex_classtype;";
	}

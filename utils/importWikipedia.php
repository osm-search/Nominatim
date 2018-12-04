<?php

require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');

$aCMDOptions
 = array(
    'Create and setup nominatim search system',
    array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
    array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
    array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

    array('create-tables', '', 0, 1, 0, 0, 'bool', 'Create wikipedia tables'),
    array('parse-articles', '', 0, 1, 0, 0, 'bool', 'Parse wikipedia articles'),
    array('link', '', 0, 1, 0, 0, 'bool', 'Try to link to existing OSM ids'),
   );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

/*
$sTestPageText = <<<EOD
{{Coord|47|N|2|E|type:country_region:FR|display=title}}
{{ Infobox Amusement park
| name = Six Flags Great Adventure
| image = [[File:SixFlagsGreatAdventure logo.png]]
| caption = Six Flags Great Adventure logo
| location = [[Jackson, New Jersey|Jackson]]
| location2 = New Jersey
| location3 = United States
| address = 1 Six Flags Boulevard<ref name="drivedir"/>
| season = March/April through October/November
| opening_date = July 1, 1974
| previous_names = Great Adventure
| area_acre = 2200
| rides = 45 park admission rides
| coasters = 12
| water_rides = 2
| owner = [[Six Flags]]
| general_manager =
| homepage = [http://www.sixflags.com/parks/greatadventure/ Six Flags Great Adventure]
}}
EOD;
var_dump(_templatesToProperties(_parseWikipediaContent($sTestPageText)));
exit;
//| coordinates = {{Coord|40|08|16.65|N|74|26|26.69|W|region:US-NJ_type:landmark|display=inline,title}}
*/
/*

    $a = array();
    $a[] = 'test';

    $oDB &= getDB();

    if ($aCMDResult['drop-tables'])
    {
        $oDB->query('DROP TABLE wikipedia_article');
        $oDB->query('DROP TABLE wikipedia_link');
    }
*/

if ($aCMDResult['create-tables']) {
    $sSQL = <<<'EOD'
CREATE TABLE wikipedia_article (
    language text NOT NULL,
    title text NOT NULL,
    langcount integer,
    othercount integer,
    totalcount integer,
    lat double precision,
    lon double precision,
    importance double precision,
    title_en text,
    osm_type character(1),
    osm_id bigint,
    infobox_type text,
    population bigint,
    website text
);
        $oDB->query($sSQL);

        $oDB->query("SELECT AddGeometryColumn('wikipedia_article', 'location', 4326, 'GEOMETRY', 2)");

        $sSQL = <<<'EOD'
CREATE TABLE wikipedia_link (
  from_id INTEGER,
  to_name text
  );
EOD;
    $oDB->query($sSQL);
}


function degreesAndMinutesToDecimal($iDegrees, $iMinutes = 0, $fSeconds = 0, $sNSEW = 'N')
{
    $sNSEW = strtoupper($sNSEW);
    return ($sNSEW == 'S' || $sNSEW == 'W'?-1:1) * ((float)$iDegrees + (float)$iMinutes/60 + (float)$fSeconds/3600);
}


function _parseWikipediaContent($sPageText)
{
    $sPageText = str_replace("\n", ' ', $sPageText);
    $sPageText = preg_replace('#<!--.*?-->#m', '', $sPageText);
    $sPageText = preg_replace('#<math>.*?<\\/math>#m', '', $sPageText);

    $aPageText = preg_split('#({{|}}|\\[\\[|\\]\\]|[|])#', $sPageText, -1, PREG_SPLIT_DELIM_CAPTURE);

    $aPageProperties = array();
    $sPageBody = '';
    $aTemplates = array();
    $aLinks = array();

    $aTemplateStack = array();
    $aState = array('body');
    foreach ($aPageText as $i => $sPart) {
        switch ($sPart) {
            case '{{':
                array_unshift($aTemplateStack, array('', array()));
                array_unshift($aState, 'template');
                break;
            case '}}':
                if ($aState[0] == 'template' || $aState[0] == 'templateparam') {
                    $aTemplate = array_shift($aTemplateStack);
                    array_shift($aState);

                    $aTemplates[] = $aTemplate;
                }
                break;
            case '[[':
                $sLinkPage = '';
                $sLinkSyn = '';
                array_unshift($aState, 'link');
                break;
            case ']]':
                if ($aState[0] == 'link' || $aState[0] == 'linksynonim') {
                    if (!$sLinkSyn) $sLinkSyn = $sLinkPage;
                    if (substr($sLinkPage, 0, 6) == 'Image:') $sLinkSyn = substr($sLinkPage, 6);

                    $aLinks[] = array($sLinkPage, $sLinkSyn);

                    array_shift($aState);
                    switch ($aState[0]) {
                        case 'template':
                            $aTemplateStack[0][0] .= trim($sPart);
                            break;
                        case 'templateparam':
                            $aTemplateStack[0][1][0] .= $sLinkSyn;
                            break;
                        case 'link':
                            $sLinkPage .= trim($sPart);
                            break;
                        case 'linksynonim':
                            $sLinkSyn .= $sPart;
                            break;
                        case 'body':
                            $sPageBody .= $sLinkSyn;
                            break;
                        default:
                            var_dump($aState, $sPageName, $aTemplateStack, $sPart, $aPageText);
                            fail('unknown state');
                    }
                }
                break;
            case '|':
                if ($aState[0] == 'template' || $aState[0] == 'templateparam') {
                    // Create a new template paramater
                    $aState[0] = 'templateparam';
                    array_unshift($aTemplateStack[0][1], '');
                }
                if ($aState[0] == 'link') $aState[0] = 'linksynonim';
                break;
            default:
                switch ($aState[0]) {
                    case 'template':
                        $aTemplateStack[0][0] .= trim($sPart);
                        break;
                    case 'templateparam':
                        $aTemplateStack[0][1][0] .= $sPart;
                        break;
                    case 'link':
                        $sLinkPage .= trim($sPart);
                        break;
                    case 'linksynonim':
                        $sLinkSyn .= $sPart;
                        break;
                    case 'body':
                        $sPageBody .= $sPart;
                        break;
                    default:
                        var_dump($aState, $aPageText);
                        fail('unknown state');
                }
                break;
        }
    }
    return $aTemplates;
}

function _templatesToProperties($aTemplates)
{
    $aPageProperties = array();
    foreach ($aTemplates as $iTemplate => $aTemplate) {
        $aParams = array();
        foreach (array_reverse($aTemplate[1]) as $iParam => $sParam) {
            if (($iPos = strpos($sParam, '=')) === false) {
                $aParams[] = trim($sParam);
            } else {
                $aParams[trim(substr($sParam, 0, $iPos))] = trim(substr($sParam, $iPos+1));
            }
        }
        $aTemplates[$iTemplate][1] = $aParams;
        if (!isset($aPageProperties['sOfficialName']) && isset($aParams['official_name']) && $aParams['official_name']) $aPageProperties['sOfficialName'] = $aParams['official_name'];
        if (!isset($aPageProperties['iPopulation']) && isset($aParams['population']) && $aParams['population'] && preg_match('#^[0-9.,]+#', $aParams['population'])) {
            $aPageProperties['iPopulation'] = (int)str_replace(array(',', '.'), '', $aParams['population']);
        }
        if (!isset($aPageProperties['iPopulation']) && isset($aParams['population_total']) && $aParams['population_total'] && preg_match('#^[0-9.,]+#', $aParams['population_total'])) {
            $aPageProperties['iPopulation'] = (int)str_replace(array(',', '.'), '', $aParams['population_total']);
        }
        if (!isset($aPageProperties['iPopulation']) && isset($aParams['population_urban']) && $aParams['population_urban'] && preg_match('#^[0-9.,]+#', $aParams['population_urban'])) {
            $aPageProperties['iPopulation'] = (int)str_replace(array(',', '.'), '', $aParams['population_urban']);
        }
        if (!isset($aPageProperties['iPopulation']) && isset($aParams['population_estimate']) && $aParams['population_estimate'] && preg_match('#^[0-9.,]+#', $aParams['population_estimate'])) {
            $aPageProperties['iPopulation'] = (int)str_replace(array(',', '.'), '', $aParams['population_estimate']);
        }
        if (!isset($aPageProperties['sWebsite']) && isset($aParams['website']) && $aParams['website']) {
            if (preg_match('#^\\[?([^ \\]]+)[^\\]]*\\]?$#', $aParams['website'], $aMatch)) {
                $aPageProperties['sWebsite'] = $aMatch[1];
                if (strpos($aPageProperties['sWebsite'], ':/'.'/') === false) {
                    $aPageProperties['sWebsite'] = 'http:/'.'/'.$aPageProperties['sWebsite'];
                }
            }
        }
        if (!isset($aPageProperties['sTopLevelDomain']) && isset($aParams['cctld']) && $aParams['cctld']) {
            $aPageProperties['sTopLevelDomain'] = str_replace(array('[', ']', '.'), '', $aParams['cctld']);
        }

        if (!isset($aPageProperties['sInfoboxType']) && strtolower(substr($aTemplate[0], 0, 7)) == 'infobox') {
            $aPageProperties['sInfoboxType'] = trim(substr($aTemplate[0], 8));
            // $aPageProperties['aInfoboxParams'] = $aParams;
        }

        // Assume the first template with lots of params is the type (fallback for infobox)
        if (!isset($aPageProperties['sPossibleInfoboxType']) && count($aParams) > 10) {
            $aPageProperties['sPossibleInfoboxType'] = trim($aTemplate[0]);
            // $aPageProperties['aInfoboxParams'] = $aParams;
        }

        // do we have a lat/lon
        if (!isset($aPageProperties['fLat'])) {
            if (isset($aParams['latd']) && isset($aParams['longd'])) {
                $aPageProperties['fLat'] = degreesAndMinutesToDecimal($aParams['latd'], @$aParams['latm'], @$aParams['lats'], @$aParams['latNS']);
                $aPageProperties['fLon'] = degreesAndMinutesToDecimal($aParams['longd'], @$aParams['longm'], @$aParams['longs'], @$aParams['longEW']);
            }
            if (isset($aParams['lat_degrees']) && isset($aParams['lat_degrees'])) {
                $aPageProperties['fLat'] = degreesAndMinutesToDecimal($aParams['lat_degrees'], @$aParams['lat_minutes'], @$aParams['lat_seconds'], @$aParams['lat_direction']);
                $aPageProperties['fLon'] = degreesAndMinutesToDecimal($aParams['long_degrees'], @$aParams['long_minutes'], @$aParams['long_seconds'], @$aParams['long_direction']);
            }
            if (isset($aParams['latitude']) && isset($aParams['longitude'])) {
                if (preg_match('#[0-9.]+#', $aParams['latitude']) && preg_match('#[0-9.]+#', $aParams['longitude'])) {
                    $aPageProperties['fLat'] = (float)$aParams['latitude'];
                    $aPageProperties['fLon'] = (float)$aParams['longitude'];
                }
            }
            if (strtolower($aTemplate[0]) == 'coord') {
                if (isset($aParams[3]) && (strtoupper($aParams[3]) == 'N' || strtoupper($aParams[3]) == 'S')) {
                    $aPageProperties['fLat'] = degreesAndMinutesToDecimal($aParams[0], $aParams[1], $aParams[2], $aParams[3]);
                    $aPageProperties['fLon'] = degreesAndMinutesToDecimal($aParams[4], $aParams[5], $aParams[6], $aParams[7]);
                } elseif (isset($aParams[0]) && isset($aParams[1]) && isset($aParams[2]) && (strtoupper($aParams[2]) == 'N' || strtoupper($aParams[2]) == 'S')) {
                    $aPageProperties['fLat'] = degreesAndMinutesToDecimal($aParams[0], $aParams[1], 0, $aParams[2]);
                    $aPageProperties['fLon'] = degreesAndMinutesToDecimal($aParams[3], $aParams[4], 0, $aParams[5]);
                } elseif (isset($aParams[0]) && isset($aParams[1]) && (strtoupper($aParams[1]) == 'N' || strtoupper($aParams[1]) == 'S')) {
                    $aPageProperties['fLat'] = (strtoupper($aParams[1]) == 'N'?1:-1) * (float)$aParams[0];
                    $aPageProperties['fLon'] = (strtoupper($aParams[3]) == 'E'?1:-1) * (float)$aParams[2];
                } elseif (isset($aParams[0]) && is_numeric($aParams[0]) && isset($aParams[1]) && is_numeric($aParams[1])) {
                    $aPageProperties['fLat'] = (float)$aParams[0];
                    $aPageProperties['fLon'] = (float)$aParams[1];
                }
            }
            if (isset($aParams['Latitude']) && isset($aParams['Longitude'])) {
                $aParams['Latitude'] = str_replace('&nbsp;', ' ', $aParams['Latitude']);
                $aParams['Longitude'] = str_replace('&nbsp;', ' ', $aParams['Longitude']);
                if (preg_match('#^([0-9]+)°( ([0-9]+)′)? ([NS]) to ([0-9]+)°( ([0-9]+)′)? ([NS])#', $aParams['Latitude'], $aMatch)) {
                    $aPageProperties['fLat'] =
                        (degreesAndMinutesToDecimal($aMatch[1], $aMatch[3], 0, $aMatch[4])
                        +degreesAndMinutesToDecimal($aMatch[5], $aMatch[7], 0, $aMatch[8])) / 2;
                } elseif (preg_match('#^([0-9]+)°( ([0-9]+)′)? ([NS])#', $aParams['Latitude'], $aMatch)) {
                    $aPageProperties['fLat'] = degreesAndMinutesToDecimal($aMatch[1], $aMatch[3], 0, $aMatch[4]);
                }

                if (preg_match('#^([0-9]+)°( ([0-9]+)′)? ([EW]) to ([0-9]+)°( ([0-9]+)′)? ([EW])#', $aParams['Longitude'], $aMatch)) {
                    $aPageProperties['fLon'] =
                        (degreesAndMinutesToDecimal($aMatch[1], $aMatch[3], 0, $aMatch[4])
                        +degreesAndMinutesToDecimal($aMatch[5], $aMatch[7], 0, $aMatch[8])) / 2;
                } elseif (preg_match('#^([0-9]+)°( ([0-9]+)′)? ([EW])#', $aParams['Longitude'], $aMatch)) {
                    $aPageProperties['fLon'] = degreesAndMinutesToDecimal($aMatch[1], $aMatch[3], 0, $aMatch[4]);
                }
            }
        }
    }
    if (isset($aPageProperties['sPossibleInfoboxType'])) {
        if (!isset($aPageProperties['sInfoboxType'])) $aPageProperties['sInfoboxType'] = '#'.$aPageProperties['sPossibleInfoboxType'];
        unset($aPageProperties['sPossibleInfoboxType']);
    }
    return $aPageProperties;
}

if (isset($aCMDResult['parse-wikipedia'])) {
    $oDB =& getDB();
    $sSQL = 'select page_title from content where page_namespace = 0 and page_id %10 = ';
    $sSQL .= $aCMDResult['parse-wikipedia'];
    $sSQL .= ' and (page_content ilike \'%{{Coord%\' or (page_content ilike \'%lat%\' and page_content ilike \'%lon%\'))';
    $aArticleNames = $oDB->getCol($sSQL);
    /* $aArticleNames = $oDB->getCol($sSQL = 'select page_title from content where page_namespace = 0
        and (page_content ilike \'%{{Coord%\' or (page_content ilike \'%lat%\'
        and page_content ilike \'%lon%\')) and page_title in (\'Virginia\')');
     */
    foreach ($aArticleNames as $sArticleName) {
        $sPageText = $oDB->getOne('select page_content from content where page_namespace = 0 and page_title = \''.pg_escape_string($sArticleName).'\'');
        $aP = _templatesToProperties(_parseWikipediaContent($sPageText));

        if (isset($aP['sInfoboxType'])) {
            $aP['sInfoboxType'] = preg_replace('#\\s+#', ' ', $aP['sInfoboxType']);
            $sSQL = 'update wikipedia_article set ';
            $sSQL .= 'infobox_type = \''.pg_escape_string($aP['sInfoboxType']).'\'';
            $sSQL .= ' where language = \'en\' and title = \''.pg_escape_string($sArticleName).'\';';
            $oDB->query($sSQL);
        }
        if (isset($aP['iPopulation'])) {
            $sSQL = 'update wikipedia_article set ';
            $sSQL .= 'population = \''.pg_escape_string($aP['iPopulation']).'\'';
            $sSQL .= ' where language = \'en\' and title = \''.pg_escape_string($sArticleName).'\';';
            $oDB->query($sSQL);
        }
        if (isset($aP['sWebsite'])) {
            $sSQL = 'update wikipedia_article set ';
            $sSQL .= 'website = \''.pg_escape_string($aP['sWebsite']).'\'';
            $sSQL .= ' where language = \'en\' and title = \''.pg_escape_string($sArticleName).'\';';
            $oDB->query($sSQL);
        }
        if (isset($aP['fLat']) && ($aP['fLat']!='-0' || $aP['fLon']!='-0')) {
            if (!isset($aP['sInfoboxType'])) $aP['sInfoboxType'] = '';
            echo $sArticleName.'|'.$aP['sInfoboxType'].'|'.$aP['fLat'].'|'.$aP['fLon'] ."\n";
            $sSQL = 'update wikipedia_article set ';
            $sSQL .= 'lat = \''.pg_escape_string($aP['fLat']).'\',';
            $sSQL .= 'lon = \''.pg_escape_string($aP['fLon']).'\'';
            $sSQL .= ' where language = \'en\' and title = \''.pg_escape_string($sArticleName).'\';';
            $oDB->query($sSQL);
        }
    }
}


function nominatimXMLStart($hParser, $sName, $aAttr)
{
    global $aNominatRecords;
    switch ($sName) {
        case 'PLACE':
            $aNominatRecords[] = $aAttr;
            break;
    }
}


function nominatimXMLEnd($hParser, $sName)
{
}


if (isset($aCMDResult['link'])) {
    $oDB =& getDB();
    $aWikiArticles = $oDB->getAll("select * from wikipedia_article where language = 'en' and lat is not null and osm_type is null and totalcount < 31 order by importance desc limit 200000");

    // If you point this script at production OSM you will be blocked
    $sNominatimBaseURL = 'http://SEVERNAME/search.php';

    foreach ($aWikiArticles as $aRecord) {
        $aRecord['name'] = str_replace('_', ' ', $aRecord['title']);

        $sURL = $sNominatimBaseURL.'?format=xml&accept-language=en';

        echo "\n-- ".$aRecord['name'].', '.$aRecord['infobox_type']."\n";
        $fMaxDist = 0.0000001;
        $bUnknown = false;
        switch (strtolower($aRecord['infobox_type'])) {
            case 'former country':
                continue 2;
            case 'sea':
                $fMaxDist = 60; // effectively turn it off
                $sURL .= '&viewbox='.($aRecord['lon']-$fMaxDist).','.($aRecord['lat']+$fMaxDist).','.($aRecord['lon']+$fMaxDist).','.($aRecord['lat']-$fMaxDist);
                break;
            case 'country':
            case 'island':
            case 'islands':
            case 'continent':
                $fMaxDist = 60; // effectively turn it off
                $sURL .= '&featuretype=country';
                $sURL .= '&viewbox='.($aRecord['lon']-$fMaxDist).','.($aRecord['lat']+$fMaxDist).','.($aRecord['lon']+$fMaxDist).','.($aRecord['lat']-$fMaxDist);
                break;
            case 'prefecture japan':
                $aRecord['name'] = trim(str_replace(' Prefecture', ' ', $aRecord['name']));
                // intentionally no break
            case 'state':
            case '#us state':
            case 'county':
            case 'u.s. state':
            case 'u.s. state symbols':
            case 'german state':
            case 'province or territory of canada':
            case 'indian jurisdiction':
            case 'province':
            case 'french region':
            case 'region of italy':
            case 'kommune':
            case '#australia state or territory':
            case 'russian federal subject':
                $fMaxDist = 4;
                $sURL .= '&featuretype=state';
                $sURL .= '&viewbox='.($aRecord['lon']-$fMaxDist).','.($aRecord['lat']+$fMaxDist).','.($aRecord['lon']+$fMaxDist).','.($aRecord['lat']-$fMaxDist);
                break;
            case 'protected area':
                $fMaxDist = 1;
                $sURL .= '&nearlat='.$aRecord['lat'];
                $sURL .= '&nearlon='.$aRecord['lon'];
                $sURL .= '&viewbox='.($aRecord['lon']-$fMaxDist).','.($aRecord['lat']+$fMaxDist).','.($aRecord['lon']+$fMaxDist).','.($aRecord['lat']-$fMaxDist);
                break;
            case 'settlement':
                $bUnknown = true;
                // intentionally no break
            case 'french commune':
            case 'italian comune':
            case 'uk place':
            case 'italian comune':
            case 'australian place':
            case 'german place':
            case '#geobox':
            case 'u.s. county':
            case 'municipality':
            case 'city japan':
            case 'russian inhabited locality':
            case 'finnish municipality/land area':
            case 'england county':
            case 'israel municipality':
            case 'russian city':
            case 'city':
                $fMaxDist = 0.2;
                $sURL .= '&featuretype=settlement';
                $sURL .= '&viewbox='.($aRecord['lon']-0.5).','.($aRecord['lat']+0.5).','.($aRecord['lon']+0.5).','.($aRecord['lat']-0.5);
                break;
            case 'mountain':
            case 'mountain pass':
            case 'river':
            case 'lake':
            case 'airport':
                $fMaxDist = 0.2;
                $sURL .= '&viewbox='.($aRecord['lon']-0.5).','.($aRecord['lat']+0.5).','.($aRecord['lon']+0.5).','.($aRecord['lat']-0.5);
                break;
            case 'ship begin':
                $fMaxDist = 0.1;
                $aTypes = array('wreck');
                $sURL .= '&viewbox='.($aRecord['lon']-0.01).','.($aRecord['lat']+0.01).','.($aRecord['lon']+0.01).','.($aRecord['lat']-0.01);
                $sURL .= '&nearlat='.$aRecord['lat'];
                $sURL .= '&nearlon='.$aRecord['lon'];
                break;
            case 'road':
            case 'university':
            case 'company':
            case 'department':
                $fMaxDist = 0.005;
                $sURL .= '&viewbox='.($aRecord['lon']-0.01).','.($aRecord['lat']+0.01).','.($aRecord['lon']+0.01).','.($aRecord['lat']-0.01);
                $sURL .= '&bounded=1';
                $sURL .= '&nearlat='.$aRecord['lat'];
                $sURL .= '&nearlon='.$aRecord['lon'];
                break;
            default:
                $bUnknown = true;
                $fMaxDist = 0.005;
                $sURL .= '&viewbox='.($aRecord['lon']-0.01).','.($aRecord['lat']+0.01).','.($aRecord['lon']+0.01).','.($aRecord['lat']-0.01);
                // $sURL .= "&bounded=1";
                $sURL .= '&nearlat='.$aRecord['lat'];
                $sURL .= '&nearlon='.$aRecord['lon'];
                echo '-- Unknown: '.$aRecord['infobox_type']."\n";
                break;
        }
        $sNameURL = $sURL.'&q='.urlencode($aRecord['name']);

        var_Dump($sNameURL);
        $sXML = file_get_contents($sNameURL);

        $aNominatRecords = array();
        $hXMLParser = xml_parser_create();
        xml_set_element_handler($hXMLParser, 'nominatimXMLStart', 'nominatimXMLEnd');
        xml_parse($hXMLParser, $sXML, true);
        xml_parser_free($hXMLParser);

        if (!isset($aNominatRecords[0])) {
            $aNameParts = preg_split('#[(,]#', $aRecord['name']);
            if (count($aNameParts) > 1) {
                $sNameURL = $sURL.'&q='.urlencode(trim($aNameParts[0]));
                var_Dump($sNameURL);
                $sXML = file_get_contents($sNameURL);

                $aNominatRecords = array();
                $hXMLParser = xml_parser_create();
                xml_set_element_handler($hXMLParser, 'nominatimXMLStart', 'nominatimXMLEnd');
                xml_parse($hXMLParser, $sXML, true);
                xml_parser_free($hXMLParser);
            }
        }

        // assume first is best/right
        for ($i = 0; $i < count($aNominatRecords); $i++) {
            $fDiff = ($aRecord['lat']-$aNominatRecords[$i]['LAT']) * ($aRecord['lat']-$aNominatRecords[$i]['LAT']);
            $fDiff += ($aRecord['lon']-$aNominatRecords[$i]['LON']) * ($aRecord['lon']-$aNominatRecords[$i]['LON']);
            $fDiff = sqrt($fDiff);
            if ($bUnknown) {
                // If it was an unknown type base it on the rank of the found result
                $iRank = (int)$aNominatRecords[$i]['PLACE_RANK'];
                if ($iRank <= 4) $fMaxDist = 2;
                elseif ($iRank <= 8) $fMaxDist = 1;
                elseif ($iRank <= 10) $fMaxDist = 0.8;
                elseif ($iRank <= 12) $fMaxDist = 0.6;
                elseif ($iRank <= 17) $fMaxDist = 0.2;
                elseif ($iRank <= 18) $fMaxDist = 0.1;
                elseif ($iRank <= 22) $fMaxDist = 0.02;
                elseif ($iRank <= 26) $fMaxDist = 0.001;
                else $fMaxDist = 0.001;
            }
            echo '-- FOUND "'.substr($aNominatRecords[$i]['DISPLAY_NAME'], 0, 50);
            echo '", '.$aNominatRecords[$i]['CLASS'].', '.$aNominatRecords[$i]['TYPE'];
            echo ', '.$aNominatRecords[$i]['PLACE_RANK'].', '.$aNominatRecords[$i]['OSM_TYPE'];
            echo " (dist:$fDiff, max:$fMaxDist)\n";
            if ($fDiff > $fMaxDist) {
                echo "-- Diff too big $fDiff (max: $fMaxDist)".$aRecord['lat'].','.$aNominatRecords[$i]['LAT'].' & '.$aRecord['lon'].','.$aNominatRecords[$i]['LON']." \n";
            } else {
                $sSQL = 'update wikipedia_article set osm_type=';
                switch ($aNominatRecords[$i]['OSM_TYPE']) {
                    case 'relation':
                        $sSQL .= "'R'";
                        break;
                    case 'way':
                        $sSQL .= "'W'";
                        break;
                    case 'node':
                        $sSQL .= "'N'";
                        break;
                }
                $sSQL .= ', osm_id='.$aNominatRecords[$i]['OSM_ID']." where language = '".pg_escape_string($aRecord['language'])."' and title = '".pg_escape_string($aRecord['title'])."'";
                $oDB->query($sSQL);
                break;
            }
        }
    }
}
